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

@router.get("/tipologias")
def listar_tipologias_canonicas(
    categoria: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    conn = _get_conn()
    if categoria:
        cur = conn.execute(
            "SELECT * FROM tipologias_canonicas WHERE categoria=? ORDER BY codigo LIMIT ? OFFSET ?",
            (categoria.upper(), limit, offset),
        )
    else:
        cur = conn.execute(
            "SELECT * FROM tipologias_canonicas ORDER BY codigo LIMIT ? OFFSET ?", (limit, offset)
        )
    rows = _rows_as_dicts(cur)
    conn.close()
    return JSONResponse({"total": len(rows), "tipologias": rows})


@router.get("/tipologias/{codigo}")
def detalhe_tipologia_canonica(codigo: str):
    conn = _get_conn()
    cur = conn.execute("SELECT * FROM tipologias_canonicas WHERE codigo=?", (codigo.upper(),))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Tipologia canônica '{codigo}' não encontrada")
    result = dict(zip([d[0] for d in cur.description], row))
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

@router.get("/ferragens")
def listar_ferragens_canonicas(
    tipo: str | None = Query(None),
    fabricante: str | None = Query(None),
    comp_min: float | None = Query(None),
    comp_max: float | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    conn = _get_conn()
    filters, params = [], []
    if tipo:
        filters.append("tipo=?")
        params.append(tipo)
    if fabricante:
        filters.append("fabricante_codigo=?")
        params.append(fabricante.upper())
    if comp_min is not None:
        filters.append("comprimento_mm >= ?")
        params.append(comp_min)
    if comp_max is not None:
        filters.append("comprimento_mm <= ?")
        params.append(comp_max)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params += [limit, offset]
    cur = conn.execute(
        f"SELECT * FROM ferragens_canonicas {where} ORDER BY codigo_normalizado LIMIT ? OFFSET ?", params
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
