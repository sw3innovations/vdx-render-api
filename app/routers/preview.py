from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import Response
from app.core.normalizer import normalizar_tipologia
from app.services import preview_generator
from app.core.constitution import listar_entries, buscar

router = APIRouter(prefix="/api/v1", tags=["preview"])


@router.get("/tipologia/{chave}/preview")
async def preview_tipologia(
    chave: str,
    regenerar: bool = Query(False, description="Forçar regeneração"),
    x_vdx_key: str = Header(None, alias="X-VDX-Key"),
):
    if not x_vdx_key:
        raise HTTPException(status_code=401, detail="X-VDX-Key obrigatório")
    chave_norm, dados = normalizar_tipologia(chave)
    if not dados:
        raise HTTPException(status_code=404, detail=f"Tipologia '{chave}' não encontrada")
    if regenerar:
        preview_generator.invalidar_cache(chave_norm)
    svg = await preview_generator.gerar_preview_async(chave_norm, dados)
    return Response(content=svg, media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.get("/tipologias/previews")
async def listar_previews(
    x_vdx_key: str = Header(None, alias="X-VDX-Key"),
):
    if not x_vdx_key:
        raise HTTPException(status_code=401, detail="X-VDX-Key obrigatório")
    entries = listar_entries(tipo="tipologia")
    resultado = []
    for e in entries:
        entry = buscar(e["chave"], tipo="tipologia")
        if entry:
            has_cache = preview_generator.get_cached_preview(e["chave"]) is not None
            resultado.append({
                "chave": e["chave"],
                "nome": entry["dados"].get("nome_display", e["chave"]),
                "preview_url": f"/api/v1/tipologia/{e['chave']}/preview",
                "cached": has_cache
            })
    return resultado


@router.post("/tipologias/previews/regenerar")
async def regenerar_todos(
    x_vdx_key: str = Header(None, alias="X-VDX-Key"),
):
    if not x_vdx_key:
        raise HTTPException(status_code=401, detail="X-VDX-Key obrigatório")
    entries = listar_entries(tipo="tipologia")
    resultados = []
    for e in entries:
        entry = buscar(e["chave"], tipo="tipologia")
        if entry:
            preview_generator.invalidar_cache(e["chave"])
            svg = await preview_generator.gerar_preview_async(e["chave"], entry["dados"])
            resultados.append({
                "chave": e["chave"],
                "bytes": len(svg),
                "status": "ok" if "<svg" in svg else "fallback"
            })
    return {"total": len(resultados), "previews": resultados}
