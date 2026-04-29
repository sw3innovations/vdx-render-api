"""Endpoints de consulta ao dump VDX — GET /api/v1/dump/*."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.constitution import _get_conn

router = APIRouter(prefix="/api/v1/dump", tags=["dump"])


def _rows_as_dicts(cursor) -> list[dict]:
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


# ── tipologias ────────────────────────────────────────────────────────────────

@router.get("/tipologias")
def listar_tipologias(
    ativo: str | None = Query(None, description="Filtrar por ID_ATIVO (S/N)"),
):
    conn = _get_conn()
    if ativo:
        cur = conn.execute(
            "SELECT * FROM dump_tipologias WHERE id_ativo=? ORDER BY nu_tip", (ativo.upper(),)
        )
    else:
        cur = conn.execute("SELECT * FROM dump_tipologias ORDER BY nu_tip")
    rows = _rows_as_dicts(cur)
    conn.close()
    return JSONResponse({"total": len(rows), "tipologias": rows})


@router.get("/tipologias/{nu_tip}")
def detalhe_tipologia(nu_tip: int):
    conn = _get_conn()
    cur = conn.execute("SELECT * FROM dump_tipologias WHERE nu_tip=?", (nu_tip,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Tipologia {nu_tip} não encontrada")
    result = dict(zip([d[0] for d in cur.description], row))
    modelos = _rows_as_dicts(
        conn.execute("SELECT * FROM dump_modelos WHERE nu_tip=? ORDER BY nu_mod", (nu_tip,))
    )
    conn.close()
    result["modelos"] = modelos
    return JSONResponse(result)


# ── modelos ───────────────────────────────────────────────────────────────────

@router.get("/modelos")
def listar_modelos(
    nu_tip: int | None = Query(None, description="Filtrar por tipologia"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    conn = _get_conn()
    if nu_tip is not None:
        cur = conn.execute(
            "SELECT * FROM dump_modelos WHERE nu_tip=? ORDER BY nu_mod LIMIT ? OFFSET ?",
            (nu_tip, limit, offset),
        )
    else:
        cur = conn.execute(
            "SELECT * FROM dump_modelos ORDER BY nu_mod LIMIT ? OFFSET ?", (limit, offset)
        )
    rows = _rows_as_dicts(cur)
    conn.close()
    return JSONResponse({"total": len(rows), "modelos": rows})


@router.get("/modelos/{nu_mod}")
def detalhe_modelo(nu_mod: int):
    conn = _get_conn()
    cur = conn.execute("SELECT * FROM dump_modelos WHERE nu_mod=?", (nu_mod,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Modelo {nu_mod} não encontrado")
    result = dict(zip([d[0] for d in cur.description], row))
    result["pecas"] = _rows_as_dicts(
        conn.execute(
            "SELECT * FROM dump_geometria_pecas WHERE nu_mod=? ORDER BY nu_peca", (nu_mod,)
        )
    )
    result["variaveis_altura"] = _rows_as_dicts(
        conn.execute("SELECT * FROM dump_variaveis_altura WHERE nu_mod=?", (nu_mod,))
    )
    result["variaveis_largura"] = _rows_as_dicts(
        conn.execute("SELECT * FROM dump_variaveis_largura WHERE nu_mod=?", (nu_mod,))
    )
    conn.close()
    return JSONResponse(result)


# ── geometria pecas ───────────────────────────────────────────────────────────

@router.get("/geometria")
def listar_geometria(
    nu_mod: int | None = Query(None),
    ds_tipo: str | None = Query(None, description="Filtrar por DS_TIPO (VI, PE, ...)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    conn = _get_conn()
    filters, params = [], []
    if nu_mod is not None:
        filters.append("nu_mod=?")
        params.append(nu_mod)
    if ds_tipo:
        filters.append("ds_tipo=?")
        params.append(ds_tipo.upper())
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params += [limit, offset]
    cur = conn.execute(
        f"SELECT * FROM dump_geometria_pecas {where} ORDER BY nu_mod, nu_peca LIMIT ? OFFSET ?",
        params,
    )
    rows = _rows_as_dicts(cur)
    conn.close()
    return JSONResponse({"total": len(rows), "pecas": rows})


# ── categorias ────────────────────────────────────────────────────────────────

@router.get("/categorias")
def listar_categorias():
    conn = _get_conn()
    rows = _rows_as_dicts(conn.execute("SELECT * FROM dump_categorias_ferragens ORDER BY nu_cat"))
    conn.close()
    return JSONResponse({"total": len(rows), "categorias": rows})


# ── variaveis ─────────────────────────────────────────────────────────────────

@router.get("/variaveis")
def listar_variaveis(
    nu_mod: int | None = Query(None),
    eixo: str | None = Query(None, description="'altura' ou 'largura'"),
):
    conn = _get_conn()
    result: dict = {}
    if eixo in (None, "altura"):
        q = "SELECT * FROM dump_variaveis_altura"
        p: list = []
        if nu_mod is not None:
            q += " WHERE nu_mod=?"
            p.append(nu_mod)
        result["variaveis_altura"] = _rows_as_dicts(conn.execute(q, p))
    if eixo in (None, "largura"):
        q = "SELECT * FROM dump_variaveis_largura"
        p = []
        if nu_mod is not None:
            q += " WHERE nu_mod=?"
            p.append(nu_mod)
        result["variaveis_largura"] = _rows_as_dicts(conn.execute(q, p))
    conn.close()
    return JSONResponse(result)
