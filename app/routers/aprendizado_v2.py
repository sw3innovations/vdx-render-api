from __future__ import annotations
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.auth import validate_api_key
from app.core.constitution import _get_conn
from app.schemas.aprendizado_v2 import (
    PendentePost,
    AliasPost,
    AlternativaPost,
    EntryPost,
    PendenteResolver,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2", tags=["aprendizado-v2"])


@router.post("/pendentes")
def criar_pendente(
    body: PendentePost,
    _auth: None = Depends(validate_api_key),
):
    conn = _get_conn()
    try:
        contexto_json = json.dumps(body.contexto) if body.contexto else None
        cur = conn.execute(
            "INSERT INTO pendentes_validacao_humana (descricao, contexto, fonte) VALUES (?, ?, ?)",
            (body.descricao, contexto_json, body.fonte),
        )
        conn.commit()
        return JSONResponse({
            "pendente_id": cur.lastrowid,
            "status": "criado",
            "descricao": body.descricao,
            "fonte": body.fonte,
        })
    finally:
        conn.close()


@router.post("/aliases")
def criar_alias(
    body: AliasPost,
    _auth: None = Depends(validate_api_key),
):
    conn = _get_conn()
    try:
        existe = conn.execute(
            "SELECT 1 FROM canonicas WHERE canonical_id = ?",
            (body.canonical_id,),
        ).fetchone()
        if not existe:
            raise HTTPException(422, f"canonical_id '{body.canonical_id}' não existe")

        cur = conn.execute(
            """INSERT OR IGNORE INTO aliases_canonicos
               (canonical_id, alias, tipo, fonte, confidence)
               VALUES (?, ?, ?, ?, ?)""",
            (body.canonical_id, body.alias, body.tipo, body.fonte, body.confidence),
        )
        conn.commit()

        status = "criado" if cur.rowcount > 0 else "ja_existia"
        row = conn.execute(
            "SELECT alias_id FROM aliases_canonicos WHERE alias = ? AND canonical_id = ?",
            (body.alias, body.canonical_id),
        ).fetchone()

        return JSONResponse({
            "alias_id": row["alias_id"] if row else None,
            "status": status,
            "alias": body.alias,
            "canonical_id": body.canonical_id,
        })
    finally:
        conn.close()


@router.post("/alternativas")
def criar_alternativa(
    body: AlternativaPost,
    _auth: None = Depends(validate_api_key),
):
    conn = _get_conn()
    try:
        if not conn.execute("SELECT 1 FROM funcoes_canonicas WHERE funcao_id = ?", (body.funcao_id,)).fetchone():
            raise HTTPException(422, f"funcao_id '{body.funcao_id}' não existe")
        if not conn.execute("SELECT 1 FROM canonicas WHERE canonical_id = ?", (body.canonical_id,)).fetchone():
            raise HTTPException(422, f"canonical_id '{body.canonical_id}' não existe")

        cur = conn.execute(
            """INSERT OR IGNORE INTO alternativas_funcionais
               (funcao_id, canonical_id, ordem_default, indicacao_uso)
               VALUES (?, ?, ?, ?)""",
            (body.funcao_id, body.canonical_id, body.ordem_default, body.indicacao_uso),
        )
        conn.commit()
        status = "criado" if cur.rowcount > 0 else "ja_existia"

        row = conn.execute(
            "SELECT alt_id FROM alternativas_funcionais WHERE funcao_id = ? AND canonical_id = ?",
            (body.funcao_id, body.canonical_id),
        ).fetchone()

        return JSONResponse({
            "alt_id": row["alt_id"] if row else None,
            "status": status,
            "funcao_id": body.funcao_id,
            "canonical_id": body.canonical_id,
        })
    finally:
        conn.close()


@router.post("/constitution/entries")
def upsert_entry(
    body: EntryPost,
    _auth: None = Depends(validate_api_key),
):
    conn = _get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM constitution_entries WHERE nicho = ? AND tipo = ? AND chave = ?",
            (body.nicho, body.tipo, body.chave),
        ).fetchone()

        conn.execute(
            """INSERT OR REPLACE INTO constitution_entries
               (nicho, tipo, chave, dados, origem, confianca, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
            (body.nicho, body.tipo, body.chave, json.dumps(body.dados), body.origem, body.confianca),
        )
        conn.commit()

        row = conn.execute(
            "SELECT id FROM constitution_entries WHERE nicho = ? AND tipo = ? AND chave = ?",
            (body.nicho, body.tipo, body.chave),
        ).fetchone()

        return JSONResponse({
            "id": row["id"] if row else None,
            "status": "atualizado" if existing else "criado",
            "chave": body.chave,
        })
    finally:
        conn.close()


@router.get("/pendentes")
def listar_pendentes(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    fonte: Optional[str] = Query(None),
    apenas_abertos: bool = Query(True),
    _auth: None = Depends(validate_api_key),
):
    conn = _get_conn()
    try:
        where = []
        params = []
        if fonte:
            where.append("fonte = ?")
            params.append(fonte)
        if apenas_abertos:
            where.append("resolucao IS NULL")

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        total_row = conn.execute(
            f"SELECT COUNT(*) AS c FROM pendentes_validacao_humana {where_sql}",
            params,
        ).fetchone()
        total = total_row["c"]

        rows = conn.execute(
            f"""SELECT pendente_id, descricao, contexto, fonte, created_at,
                       resolucao, validado_por, resolvido_em, nota_resolucao
                FROM pendentes_validacao_humana
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()

        items = []
        for r in rows:
            d = dict(r)
            if d.get("contexto"):
                try:
                    d["contexto"] = json.loads(d["contexto"])
                except (json.JSONDecodeError, TypeError):
                    pass
            items.append(d)

        return JSONResponse({
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        })
    finally:
        conn.close()


@router.patch("/pendentes/{pendente_id}/resolver")
def resolver_pendente(
    pendente_id: int,
    body: PendenteResolver,
    _auth: None = Depends(validate_api_key),
):
    conn = _get_conn()
    try:
        pendente = conn.execute(
            "SELECT * FROM pendentes_validacao_humana WHERE pendente_id = ?",
            (pendente_id,),
        ).fetchone()
        if not pendente:
            raise HTTPException(404, f"pendente_id {pendente_id} não encontrado")

        if pendente["resolucao"]:
            raise HTTPException(409, f"pendente já resolvido como '{pendente['resolucao']}'")

        conn.execute(
            """UPDATE pendentes_validacao_humana
               SET resolucao = ?, validado_por = ?, resolvido_em = datetime('now'), nota_resolucao = ?
               WHERE pendente_id = ?""",
            (body.resolucao, body.validado_por, body.nota, pendente_id),
        )

        promovido = None
        if body.resolucao == "aprovado" and body.promover_para != "nenhum" and body.dados_promocao:
            d = body.dados_promocao
            try:
                if body.promover_para == "alias":
                    cur = conn.execute(
                        """INSERT OR IGNORE INTO aliases_canonicos
                           (canonical_id, alias, tipo, fonte, confidence)
                           VALUES (?, ?, ?, ?, ?)""",
                        (d.get("canonical_id"), d.get("alias"), d.get("tipo", "outro"),
                         f"resolver_{body.validado_por}", d.get("confidence", "alto")),
                    )
                    promovido = {"tipo": "alias", "rowcount": cur.rowcount}

                elif body.promover_para == "alternativa":
                    cur = conn.execute(
                        """INSERT OR IGNORE INTO alternativas_funcionais
                           (funcao_id, canonical_id, ordem_default, indicacao_uso)
                           VALUES (?, ?, ?, ?)""",
                        (d.get("funcao_id"), d.get("canonical_id"),
                         d.get("ordem_default", 99), d.get("indicacao_uso")),
                    )
                    promovido = {"tipo": "alternativa", "rowcount": cur.rowcount}

                elif body.promover_para == "entry":
                    conn.execute(
                        """INSERT OR REPLACE INTO constitution_entries
                           (nicho, tipo, chave, dados, origem, confianca, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
                        (d.get("nicho", "vidros"), d.get("tipo"), d.get("chave"),
                         json.dumps(d.get("dados", {})), f"resolver_{body.validado_por}",
                         d.get("confianca", 0.9)),
                    )
                    promovido = {"tipo": "entry", "chave": d.get("chave")}
            except Exception as e:
                log.error("Erro na promoção: %s", e)
                conn.rollback()
                raise HTTPException(500, f"erro na promoção: {e}")

        conn.commit()
        return JSONResponse({
            "pendente_id": pendente_id,
            "resolucao": body.resolucao,
            "validado_por": body.validado_por,
            "promovido": promovido,
        })
    finally:
        conn.close()
