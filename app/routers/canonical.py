"""Endpoints de consulta ao schema canônico — GET /api/v1/canonical/*."""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.constitution import _get_conn

router = APIRouter(prefix="/api/v1/canonical", tags=["canonical"])


def _extract_canonical_id(code: str) -> str:
    """Extrai canonical_id (número base) de qualquer formato de código.
    Ex: 'SM-1101SG' → '1101', 'HE 1101A' → '1101', '1101' → '1101'.
    """
    m = re.search(r"\d{4}", code)
    return m.group(0) if m else code


def _rows_as_dicts(cursor) -> list[dict]:
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


# ── materiais ─────────────────────────────────────────────────────────────────

@router.get("/materiais")
def listar_materiais():
    conn = _get_conn()
    rows = _rows_as_dicts(conn.execute("SELECT * FROM materiais_canonicos ORDER BY codigo"))
    conn.close()
    return JSONResponse({"total": len(rows), "materiais": rows})


# ── acabamentos ───────────────────────────────────────────────────────────────

@router.get("/acabamentos")
def listar_acabamentos():
    conn = _get_conn()
    rows = _rows_as_dicts(conn.execute("SELECT * FROM acabamentos_canonicos ORDER BY codigo"))
    conn.close()
    return JSONResponse({"total": len(rows), "acabamentos": rows})


# ── variaveis ─────────────────────────────────────────────────────────────────

@router.get("/variaveis")
def listar_variaveis(
    eixo: str | None = Query(None, description="'altura', 'largura' ou 'neutro'"),
):
    conn = _get_conn()
    if eixo:
        cur = conn.execute(
            "SELECT * FROM variaveis_canonicas WHERE eixo=? ORDER BY codigo", (eixo.lower(),)
        )
    else:
        cur = conn.execute("SELECT * FROM variaveis_canonicas ORDER BY eixo, codigo")
    rows = _rows_as_dicts(cur)
    conn.close()
    return JSONResponse({"total": len(rows), "variaveis": rows})


# ── tipologias ────────────────────────────────────────────────────────────────

_TEM_RENDERER_SQL = """
    SELECT tc.*,
           CASE WHEN ce.chave IS NOT NULL THEN 1 ELSE 0 END AS tem_renderer
    FROM tipologias_canonicas tc
    LEFT JOIN constitution_entries ce
           ON ce.chave = tc.codigo
          AND ce.tipo  = 'tipologia'
          AND ce.nicho = 'vidros'
    WHERE tc.codigo != 'SEM_TIPOLOGIA'
"""


@router.get("/tipologias")
def listar_tipologias_canonicas(
    categoria: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    conn = _get_conn()
    if categoria:
        cur = conn.execute(
            f"{_TEM_RENDERER_SQL} AND tc.categoria=? ORDER BY tc.codigo LIMIT ? OFFSET ?",
            (categoria.upper(), limit, offset),
        )
    else:
        cur = conn.execute(
            f"{_TEM_RENDERER_SQL} ORDER BY tc.codigo LIMIT ? OFFSET ?",
            (limit, offset),
        )
    rows = _rows_as_dicts(cur)
    for r in rows:
        r["tem_renderer"] = bool(r.get("tem_renderer", 0))
    conn.close()
    return JSONResponse({"total": len(rows), "tipologias": rows})


@router.get("/tipologias/{codigo}")
def detalhe_tipologia_canonica(codigo: str):
    conn = _get_conn()
    cur = conn.execute(
        """SELECT tc.*,
                  CASE WHEN ce.chave IS NOT NULL THEN 1 ELSE 0 END AS tem_renderer
           FROM tipologias_canonicas tc
           LEFT JOIN constitution_entries ce
                  ON ce.chave = tc.codigo
                 AND ce.tipo  = 'tipologia'
                 AND ce.nicho = 'vidros'
           WHERE tc.codigo=?""",
        (codigo.upper(),),
    )
    row = cur.fetchone()
    if row is None:
        # Try lowercase for constitution-style codes (e.g. porta_abrir)
        cur = conn.execute(
            """SELECT tc.*,
                      CASE WHEN ce.chave IS NOT NULL THEN 1 ELSE 0 END AS tem_renderer
               FROM tipologias_canonicas tc
               LEFT JOIN constitution_entries ce
                      ON ce.chave = tc.codigo
                     AND ce.tipo  = 'tipologia'
                     AND ce.nicho = 'vidros'
               WHERE tc.codigo=?""",
            (codigo.lower(),),
        )
        row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Tipologia canônica '{codigo}' não encontrada")
    result = dict(zip([d[0] for d in cur.description], row))
    result["tem_renderer"] = bool(result.get("tem_renderer", 0))
    modelos = _rows_as_dicts(
        conn.execute("SELECT * FROM modelos_canonicos WHERE tipologia_id=? ORDER BY nu_mod_dump", (result["id"],))
    )
    conn.close()
    result["modelos"] = modelos
    return JSONResponse(result)


# ── modelos ───────────────────────────────────────────────────────────────────

@router.get("/modelos")
def listar_modelos_canonicos(
    tipologia_id: int | None = Query(None),
    nome_inferido: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    conn = _get_conn()
    filters, params = [], []
    if tipologia_id is not None:
        filters.append("tipologia_id=?")
        params.append(tipologia_id)
    if nome_inferido is not None:
        filters.append("nome_inferido=?")
        params.append(int(nome_inferido))
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params += [limit, offset]
    cur = conn.execute(
        f"SELECT * FROM modelos_canonicos {where} ORDER BY nu_mod_dump LIMIT ? OFFSET ?", params
    )
    rows = _rows_as_dicts(cur)
    conn.close()
    return JSONResponse({"total": len(rows), "modelos": rows})


# ── ferragens ─────────────────────────────────────────────────────────────────

# Tipo families — meta-tipo expands to all shape subtypes via IN clause
_PUXADOR_TIPOS: tuple[str, ...] = (
    "puxador", "barra", "bola", "h", "u", "concha", "capsula",
)
_DOBRADICA_TIPOS: tuple[str, ...] = (
    "dobradica", "dobradica_basculante", "dobradica_batente", "dobradica_box",
)


def _tipo_filter(tipo: str | None) -> tuple[str, list]:
    """Return (sql_fragment, params) for a tipo filter on ferragens_canonicas fc."""
    if not tipo:
        return "", []
    t = tipo.lower()
    if t == "puxador":
        ph = ",".join("?" * len(_PUXADOR_TIPOS))
        return f"fc.tipo IN ({ph})", list(_PUXADOR_TIPOS)
    if t == "dobradica":
        ph = ",".join("?" * len(_DOBRADICA_TIPOS))
        return f"fc.tipo IN ({ph})", list(_DOBRADICA_TIPOS)
    return "fc.tipo=?", [tipo]


@router.get("/ferragens/filtros")
def filtros_ferragens(tipo: str | None = Query(None)):
    conn = _get_conn()
    cond, cparams = _tipo_filter(tipo)

    # fabricantes — exclude test fixtures that start with TEST_ or FAB_
    fab_cond = (cond + " AND " if cond else "") + "f.id NOT LIKE 'TEST_%' AND f.id NOT LIKE 'FAB_%'"
    fab_rows = conn.execute(
        f"""SELECT DISTINCT f.id, f.nome FROM ferragens_canonicas fc
            JOIN fabricantes f ON f.id = fc.fabricante_codigo
            WHERE {fab_cond} ORDER BY f.nome""",
        cparams,
    ).fetchall()

    # subtipos — distinct tipos in filtered set, excluding the meta tipo itself
    sub_cond = (cond + " AND " if cond else "") + "fc.tipo IS NOT NULL"
    sub_rows = conn.execute(
        f"SELECT DISTINCT fc.tipo FROM ferragens_canonicas fc WHERE {sub_cond} ORDER BY fc.tipo",
        cparams,
    ).fetchall()
    meta_tipo = tipo.lower() if tipo else None

    # comprimento range
    comp_cond = (cond + " AND " if cond else "") + "fc.comprimento_mm IS NOT NULL"
    comp_row = conn.execute(
        f"SELECT MIN(fc.comprimento_mm), MAX(fc.comprimento_mm) FROM ferragens_canonicas fc WHERE {comp_cond}",
        cparams,
    ).fetchone()

    conn.close()
    return JSONResponse({
        "fabricantes": [{"id": r[0], "nome": r[1]} for r in fab_rows],
        "subtipos": [r[0] for r in sub_rows if r[0] != meta_tipo],
        "comprimento_min": comp_row[0] if comp_row else None,
        "comprimento_max": comp_row[1] if comp_row else None,
    })


@router.get("/ferragens")
def listar_ferragens_canonicas(
    tipo: str | None = Query(None),
    subtipo: str | None = Query(None),
    fabricante: str | None = Query(None),
    variant: str | None = Query(None, description="Alias para fabricante (filtro por fabricante/sufixo)"),
    busca: str | None = Query(None),
    comp_min: float | None = Query(None),
    comp_max: float | None = Query(None),
    canonical_id: str | None = Query(None, description="Filtra por canonical_id (código base, ex: '1101')"),
    id: str | None = Query(None, description="Compat legada: 'SM-1101SG' → retorna a variante correspondente"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    conn = _get_conn()
    cond, params = _tipo_filter(tipo)
    filters = [cond] if cond else []

    if subtipo:
        filters.append("fc.tipo=?")
        params.append(subtipo.lower())

    # ?fabricante e ?variant são equivalentes
    fab_filter = fabricante or variant
    if fab_filter:
        filters.append("fc.fabricante_codigo=?")
        params.append(fab_filter.upper())

    if busca:
        filters.append("fc.nome_apresentacao LIKE ?")
        params.append(f"%{busca}%")
    if comp_min is not None:
        filters.append("fc.comprimento_mm >= ?")
        params.append(comp_min)
    if comp_max is not None:
        filters.append("fc.comprimento_mm <= ?")
        params.append(comp_max)

    # ?canonical_id filtra por código base (ex: '1101')
    if canonical_id:
        filters.append("fc.codigo_normalizado=?")
        params.append(canonical_id)

    # Compatibilidade legada: ?id=SM-1101SG → extrai canonical_id e filtra
    if id and not canonical_id:
        extracted = _extract_canonical_id(id)
        filters.append("fc.codigo_normalizado=?")
        params.append(extracted)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params += [limit, offset]
    cur = conn.execute(
        f"""SELECT fc.*,
                   fc.codigo_normalizado AS canonical_id,
                   f.nome AS fabricante_nome,
                   m.nome_apresentacao AS material_nome,
                   a.nome_apresentacao AS acabamento_nome
            FROM ferragens_canonicas fc
            LEFT JOIN fabricantes f ON f.id = fc.fabricante_codigo
            LEFT JOIN materiais_canonicos m ON m.id = fc.material_id
            LEFT JOIN acabamentos_canonicos a ON a.id = fc.acabamento_id
            {where}
            ORDER BY fc.codigo_normalizado LIMIT ? OFFSET ?""",
        params,
    )
    rows = _rows_as_dicts(cur)
    conn.close()
    return JSONResponse({"total": len(rows), "ferragens": rows})


# ── ferragem canônica — detalhe com variantes ────────────────────────────────

@router.get("/ferragens/{cid}/variantes")
def variantes_ferragem_canonica(cid: str):
    """
    Retorna uma entrada canônica com todas as variantes (fabricantes) agrupadas.

    Exemplo: GET /api/v1/canonical/ferragens/1101/variantes
    → { canonical_id: "1101", variantes: [{...SM}, {...HE}, {...AL}] }
    """
    conn = _get_conn()
    cur = conn.execute(
        """SELECT fc.*,
                  fc.codigo_normalizado AS canonical_id,
                  f.nome AS fabricante_nome,
                  m.nome_apresentacao AS material_nome,
                  a.nome_apresentacao AS acabamento_nome
           FROM ferragens_canonicas fc
           LEFT JOIN fabricantes f ON f.id = fc.fabricante_codigo
           LEFT JOIN materiais_canonicos m ON m.id = fc.material_id
           LEFT JOIN acabamentos_canonicos a ON a.id = fc.acabamento_id
           WHERE fc.codigo_normalizado=?
           ORDER BY fc.fabricante_codigo""",
        (cid,),
    )
    rows = _rows_as_dicts(cur)
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail=f"Ferragem canônica '{cid}' não encontrada")

    # Monta resposta canônica agrupada
    first = rows[0]
    return JSONResponse({
        "canonical_id": cid,
        "tipo": first.get("tipo"),
        "subtipo": first.get("subtipo"),
        "nome_apresentacao": first.get("nome_apresentacao"),
        "variantes": rows,
        "total_variantes": len(rows),
    })


# ── auditoria ─────────────────────────────────────────────────────────────────

@router.get("/etl/auditoria")
def listar_auditoria(
    estagio: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    conn = _get_conn()
    if estagio:
        cur = conn.execute(
            "SELECT * FROM etl_auditoria WHERE estagio=? ORDER BY timestamp DESC LIMIT ?",
            (estagio, limit),
        )
    else:
        cur = conn.execute(
            "SELECT * FROM etl_auditoria ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
    rows = _rows_as_dicts(cur)
    conn.close()
    return JSONResponse({"total": len(rows), "auditoria": rows})
