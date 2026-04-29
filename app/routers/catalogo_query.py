"""Endpoints de consulta ao catálogo de puxadores — GET /api/v1/catalogo-pdf/*."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.constitution import _get_conn

router = APIRouter(prefix="/api/v1/catalogo-pdf", tags=["catalogo"])


def _rows_as_dicts(cursor) -> list[dict]:
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


# ── fabricantes ───────────────────────────────────────────────────────────────

@router.get("/fabricantes")
def listar_fabricantes():
    conn = _get_conn()
    rows = _rows_as_dicts(conn.execute("SELECT * FROM catalogo_fabricantes ORDER BY codigo"))
    conn.close()
    return JSONResponse({"total": len(rows), "fabricantes": rows})


# ── puxadores ─────────────────────────────────────────────────────────────────

@router.get("/puxadores")
def listar_puxadores(
    fabricante: str | None = Query(None, description="Código do fabricante (ex: AL, BELLNOX)"),
    tipo_visual: str | None = Query(None, description="barra|bola|capsula|h|u|concha|outro"),
    material: str | None = Query(None),
    comp_min: float | None = Query(None, description="Comprimento mínimo em mm"),
    comp_max: float | None = Query(None, description="Comprimento máximo em mm"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    conn = _get_conn()
    filters, params = [], []
    if fabricante:
        filters.append("fabricante_id=?")
        params.append(fabricante.upper())
    if tipo_visual:
        filters.append("tipo_visual=?")
        params.append(tipo_visual.lower())
    if material:
        filters.append("material LIKE ?")
        params.append(f"%{material.lower()}%")
    if comp_min is not None:
        filters.append("comp_mm >= ?")
        params.append(comp_min)
    if comp_max is not None:
        filters.append("comp_mm <= ?")
        params.append(comp_max)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params += [limit, offset]
    cur = conn.execute(
        f"SELECT * FROM catalogo_puxadores {where} ORDER BY fabricante_id, id LIMIT ? OFFSET ?",
        params,
    )
    rows = _rows_as_dicts(cur)
    total_cur = conn.execute(
        f"SELECT COUNT(*) FROM catalogo_puxadores {where}", params[:-2]
    )
    total = total_cur.fetchone()[0]
    conn.close()
    return JSONResponse({"total": total, "limit": limit, "offset": offset, "puxadores": rows})


@router.get("/puxadores/{id}")
def detalhe_puxador(id: int):
    conn = _get_conn()
    cur = conn.execute("SELECT * FROM catalogo_puxadores WHERE id=?", (id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Puxador {id} não encontrado")
    result = dict(zip([d[0] for d in cur.description], row))
    conn.close()
    return JSONResponse(result)


@router.get("/puxadores/buscar/{codigo}")
def buscar_por_codigo(codigo: str):
    import re
    norm = re.sub(r"[\s\-/]", "", codigo).upper()
    conn = _get_conn()
    cur = conn.execute(
        "SELECT * FROM catalogo_puxadores WHERE codigo_normalizado=? ORDER BY fabricante_id",
        (norm,),
    )
    rows = _rows_as_dicts(cur)
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Código '{codigo}' não encontrado")
    return JSONResponse({"total": len(rows), "puxadores": rows})


# ── stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
def stats_catalogo():
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM catalogo_puxadores").fetchone()[0]
    por_fab = _rows_as_dicts(
        conn.execute(
            "SELECT fabricante_id, COUNT(*) as total FROM catalogo_puxadores GROUP BY fabricante_id ORDER BY fabricante_id"
        )
    )
    por_tipo = _rows_as_dicts(
        conn.execute(
            "SELECT tipo_visual, COUNT(*) as total FROM catalogo_puxadores GROUP BY tipo_visual ORDER BY total DESC"
        )
    )
    conn.close()
    return JSONResponse({"total_produtos": total, "por_fabricante": por_fab, "por_tipo_visual": por_tipo})


# ── sugestão para o render ────────────────────────────────────────────────────

@router.get("/sugerir")
def sugerir_puxador(
    tipo_visual: str | None = Query(None),
    comp_mm: float | None = Query(None),
    diametro_mm: float | None = Query(None),
    limit: int = Query(5, ge=1, le=20),
):
    conn = _get_conn()
    filters, params = [], []
    if tipo_visual:
        filters.append("tipo_visual=?")
        params.append(tipo_visual.lower())
    if comp_mm is not None:
        filters.append("ABS(COALESCE(comp_mm,0) - ?) <= 50")
        params.append(comp_mm)
    if diametro_mm is not None:
        filters.append("ABS(COALESCE(diametro_mm,0) - ?) <= 5")
        params.append(diametro_mm)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params.append(limit)
    cur = conn.execute(
        f"SELECT * FROM catalogo_puxadores {where} LIMIT ?", params
    )
    rows = _rows_as_dicts(cur)
    conn.close()
    return JSONResponse({"sugestoes": rows})
