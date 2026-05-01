"""Endpoints v2 de ferragens canônicas — GET /api/v2/ferragens/*.

Queries nas tabelas v2: canonicas, variantes_canonicas, aliases_canonicos,
kits_canonicos, kits_componentes, regras_globais.

Resolução de alias: ?q=114 → aliases_canonicos → canonical_id=1114.
v1 endpoints em /api/v1/canonical/* permanecem inalterados.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.constitution import _get_conn

router = APIRouter(prefix="/api/v2/ferragens", tags=["ferragens-v2"])


def _rows_as_dicts(cursor) -> list[dict]:
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _resolve_canonical_id(conn, q: str) -> str | None:
    """Resolve q para canonical_id: match direto ou via aliases_canonicos."""
    row = conn.execute(
        "SELECT canonical_id FROM canonicas WHERE canonical_id=?", (q,)
    ).fetchone()
    if row:
        return row[0]
    alias_row = conn.execute(
        "SELECT canonical_id FROM aliases_canonicos WHERE LOWER(alias)=LOWER(?)", (q,)
    ).fetchone()
    if alias_row:
        return alias_row[0]
    return None


# ── buscar (alias-aware) ──────────────────────────────────────────────────────

@router.get("/buscar")
def buscar_ferragem(q: str = Query(..., min_length=1, description="canonical_id ou alias (ex: '114', '1114', 'gv')")):
    """Busca por canonical_id direto ou via alias. '114' resolve para '1114' via truncamento."""
    conn = _get_conn()
    cid = _resolve_canonical_id(conn, q)
    if not cid:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ferragem '{q}' não encontrada")

    rows = _rows_as_dicts(conn.execute("SELECT * FROM canonicas WHERE canonical_id=?", (cid,)))
    if not rows:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ferragem '{q}' não encontrada")
    canonical = rows[0]

    aliases = _rows_as_dicts(
        conn.execute(
            "SELECT alias, tipo, fonte, confidence FROM aliases_canonicos WHERE canonical_id=?",
            (cid,),
        )
    )
    variantes = _rows_as_dicts(
        conn.execute(
            "SELECT * FROM variantes_canonicas WHERE canonical_id=? ORDER BY fabricante_codigo",
            (cid,),
        )
    )
    conn.close()

    return JSONResponse({
        **canonical,
        "aliases": aliases,
        "variantes": variantes,
        "total_variantes": len(variantes),
        "resolved_from": q if q != cid else None,
    })


# ── filtros ───────────────────────────────────────────────────────────────────

@router.get("/filtros")
def filtros_v2():
    """Retorna valores disponíveis de linha e categoria nas canonicas."""
    conn = _get_conn()
    linhas = [r[0] for r in conn.execute(
        "SELECT DISTINCT linha FROM canonicas ORDER BY linha"
    ).fetchall()]
    categorias = [r[0] for r in conn.execute(
        "SELECT DISTINCT categoria FROM canonicas ORDER BY categoria"
    ).fetchall()]
    total = conn.execute("SELECT COUNT(*) FROM canonicas").fetchone()[0]
    conn.close()
    return JSONResponse({"total_canonicals": total, "linhas": linhas, "categorias": categorias})


# ── kits ──────────────────────────────────────────────────────────────────────

@router.get("/kits")
def listar_kits(
    fabricante_origem: str | None = Query(None),
    tipologia: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista kits canônicos com contagem de componentes."""
    conn = _get_conn()
    filters, params = [], []
    if fabricante_origem:
        filters.append("fabricante_origem=?")
        params.append(fabricante_origem)
    if tipologia:
        filters.append("tipologia=?")
        params.append(tipologia)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params += [limit, offset]

    kits = _rows_as_dicts(conn.execute(
        f"SELECT * FROM kits_canonicos {where} ORDER BY kit_id LIMIT ? OFFSET ?", params
    ))
    for kit in kits:
        n = conn.execute(
            "SELECT COUNT(*) FROM kits_componentes WHERE kit_id=?", (kit["kit_id"],)
        ).fetchone()[0]
        kit["total_componentes"] = n

    conn.close()
    return JSONResponse({"total": len(kits), "kits": kits})


@router.get("/kits/{kit_id}")
def detalhe_kit(kit_id: str):
    """Detalhe de um kit com todos os componentes."""
    conn = _get_conn()
    cur = conn.execute("SELECT * FROM kits_canonicos WHERE kit_id=?", (kit_id,))
    rows = _rows_as_dicts(cur)
    if not rows:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Kit '{kit_id}' não encontrado")

    kit = rows[0]
    componentes = _rows_as_dicts(conn.execute(
        """SELECT kc.canonical_id, kc.quantidade, kc.obrigatorio,
                  c.nome_apresentacao, c.categoria, c.linha
           FROM kits_componentes kc
           LEFT JOIN canonicas c ON c.canonical_id = kc.canonical_id
           WHERE kc.kit_id=?
           ORDER BY kc.canonical_id""",
        (kit_id,),
    ))
    conn.close()
    kit["componentes"] = componentes
    return JSONResponse(kit)


# ── regras NBR ────────────────────────────────────────────────────────────────

@router.get("/regras")
def listar_regras(categoria: str | None = Query(None)):
    """Lista regras globais (folgas NBR 7199 e outras)."""
    conn = _get_conn()
    if categoria:
        rows = _rows_as_dicts(conn.execute(
            "SELECT * FROM regras_globais WHERE categoria=? ORDER BY regra_id",
            (categoria,),
        ))
    else:
        rows = _rows_as_dicts(conn.execute(
            "SELECT * FROM regras_globais ORDER BY categoria, regra_id"
        ))
    conn.close()
    return JSONResponse({"total": len(rows), "regras": rows})


# ── list canonicals ───────────────────────────────────────────────────────────

@router.get("/")
def listar_canonicals(
    linha: str | None = Query(None),
    categoria: str | None = Query(None),
    busca: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista canônicos v2 com filtros opcionais."""
    conn = _get_conn()
    filters, params = [], []
    if linha:
        filters.append("linha=?")
        params.append(linha)
    if categoria:
        filters.append("categoria=?")
        params.append(categoria)
    if busca:
        filters.append("nome_apresentacao LIKE ?")
        params.append(f"%{busca}%")
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params += [limit, offset]

    rows = _rows_as_dicts(conn.execute(
        f"SELECT * FROM canonicas {where} ORDER BY canonical_id LIMIT ? OFFSET ?", params
    ))
    conn.close()
    return JSONResponse({"total": len(rows), "canonicals": rows})


# ── detalhe canonical ─────────────────────────────────────────────────────────

@router.get("/{cid}")
def detalhe_canonical(cid: str):
    """Detalhe de um canonical com aliases e variantes."""
    conn = _get_conn()
    cur = conn.execute("SELECT * FROM canonicas WHERE canonical_id=?", (cid,))
    rows = _rows_as_dicts(cur)
    if not rows:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Canonical '{cid}' não encontrado")

    canonical = rows[0]
    aliases = _rows_as_dicts(conn.execute(
        "SELECT alias, tipo, fonte, confidence FROM aliases_canonicos WHERE canonical_id=?",
        (cid,),
    ))
    variantes = _rows_as_dicts(conn.execute(
        "SELECT * FROM variantes_canonicas WHERE canonical_id=? ORDER BY fabricante_codigo",
        (cid,),
    ))
    conn.close()
    canonical["aliases"] = aliases
    canonical["variantes"] = variantes
    canonical["total_variantes"] = len(variantes)
    return JSONResponse(canonical)


# ── variantes de um canonical ─────────────────────────────────────────────────

@router.get("/{cid}/variantes")
def variantes_canonical(cid: str):
    """Lista variantes (por fabricante) de um canonical."""
    conn = _get_conn()
    exists = conn.execute(
        "SELECT 1 FROM canonicas WHERE canonical_id=?", (cid,)
    ).fetchone()
    if not exists:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Canonical '{cid}' não encontrado")

    rows = _rows_as_dicts(conn.execute(
        "SELECT * FROM variantes_canonicas WHERE canonical_id=? ORDER BY fabricante_codigo",
        (cid,),
    ))
    conn.close()
    return JSONResponse({"canonical_id": cid, "total_variantes": len(rows), "variantes": rows})
