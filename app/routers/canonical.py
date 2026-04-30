"""Endpoints de consulta ao schema canônico — GET /api/v1/canonical/*."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.constitution import _get_conn

router = APIRouter(prefix="/api/v1/canonical", tags=["canonical"])


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

# Shape subtypes that belong to the puxador meta-category
_PUXADOR_TIPOS: tuple[str, ...] = (
    "puxador", "barra", "bola", "h", "u", "concha", "capsula",
)


def _tipo_filter(tipo: str | None) -> tuple[str, list]:
    """Return (sql_fragment, params) for a tipo filter on ferragens_canonicas fc."""
    if not tipo:
        return "", []
    if tipo.lower() == "puxador":
        ph = ",".join("?" * len(_PUXADOR_TIPOS))
        return f"fc.tipo IN ({ph})", list(_PUXADOR_TIPOS)
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

    # shape subtipos (all _PUXADOR_TIPOS except the meta 'puxador')
    shape_tipos = [t for t in _PUXADOR_TIPOS if t != "puxador"]
    sh_ph = ",".join("?" * len(shape_tipos))
    sub_cond = (cond + " AND " if cond else "") + f"fc.tipo IN ({sh_ph})"
    sub_rows = conn.execute(
        f"SELECT DISTINCT fc.tipo FROM ferragens_canonicas fc WHERE {sub_cond} ORDER BY fc.tipo",
        cparams + shape_tipos,
    ).fetchall()

    # comprimento range
    comp_cond = (cond + " AND " if cond else "") + "fc.comprimento_mm IS NOT NULL"
    comp_row = conn.execute(
        f"SELECT MIN(fc.comprimento_mm), MAX(fc.comprimento_mm) FROM ferragens_canonicas fc WHERE {comp_cond}",
        cparams,
    ).fetchone()

    conn.close()
    return JSONResponse({
        "fabricantes": [{"id": r[0], "nome": r[1]} for r in fab_rows],
        "subtipos": [r[0] for r in sub_rows],
        "comprimento_min": comp_row[0] if comp_row else None,
        "comprimento_max": comp_row[1] if comp_row else None,
    })


@router.get("/ferragens")
def listar_ferragens_canonicas(
    tipo: str | None = Query(None),
    subtipo: str | None = Query(None),
    fabricante: str | None = Query(None),
    busca: str | None = Query(None),
    comp_min: float | None = Query(None),
    comp_max: float | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    conn = _get_conn()
    cond, params = _tipo_filter(tipo)
    filters = [cond] if cond else []

    if subtipo:
        filters.append("fc.tipo=?")
        params.append(subtipo.lower())
    if fabricante:
        filters.append("fc.fabricante_codigo=?")
        params.append(fabricante.upper())
    if busca:
        filters.append("fc.nome_apresentacao LIKE ?")
        params.append(f"%{busca}%")
    if comp_min is not None:
        filters.append("fc.comprimento_mm >= ?")
        params.append(comp_min)
    if comp_max is not None:
        filters.append("fc.comprimento_mm <= ?")
        params.append(comp_max)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params += [limit, offset]
    cur = conn.execute(
        f"""SELECT fc.*,
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
