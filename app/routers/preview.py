"""Router de previews — serve SVG animado e listagem de tipologias."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from app.core.normalizer import normalizar_tipologia
from app.services import preview_generator
from app.core.constitution import listar_entries, buscar
from app.core.auth import validate_api_key
from app.core.limiter import limiter

router = APIRouter(prefix="/api/v1", tags=["preview"])


@router.get("/tipologia/{chave}/preview")
@limiter.limit("60/minute")
async def preview_tipologia(
    request: Request,
    chave: str,
    regenerar: bool = Query(False, description="Forçar regeneração"),
    highlight: str = Query(None, description="Nome da peça pra destacar"),
):  # public: browser <img> cannot send headers
    """Retorna SVG animado do preview de uma tipologia."""
    chave_norm, dados = normalizar_tipologia(chave)
    if not dados:
        raise HTTPException(status_code=404, detail=f"Tipologia '{chave}' não encontrada")
    if regenerar:
        preview_generator.invalidar_cache(chave_norm)
    svg = await preview_generator.gerar_preview_async(chave_norm, dados)
    if highlight:
        svg = preview_generator.aplicar_destaque(svg, highlight)
    cache = "no-cache" if highlight else "public, max-age=86400"
    return Response(content=svg, media_type="image/svg+xml",
                    headers={"Cache-Control": cache})


@router.get("/tipologias/previews")
@limiter.limit("30/minute")
async def listar_previews(
    request: Request,
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
):  # public: gallery listing used by unauthenticated browser
    """Lista previews de tipologias disponíveis com paginação."""
    entries = listar_entries(tipo="tipologia")
    all_items = []
    for e in entries:
        entry = buscar(e["chave"], tipo="tipologia")
        if entry:
            has_cache = preview_generator.get_cached_preview(e["chave"]) is not None
            all_items.append({
                "chave": e["chave"],
                "nome": entry["dados"].get("nome_display", e["chave"]),
                "preview_url": f"/api/v1/tipologia/{e['chave']}/preview",
                "cached": has_cache,
            })
    total = len(all_items)
    start = (page - 1) * per_page
    return {
        "items": all_items[start:start + per_page],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


@router.post("/tipologias/previews/regenerar")
@limiter.limit("5/minute")
async def regenerar_todos(
    request: Request,
    _auth: None = Depends(validate_api_key),
):
    """Invalida e regenera os previews SVG de todas as tipologias cadastradas."""
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
                "status": "ok" if "<svg" in svg else "fallback",
            })
    return {"total": len(resultados), "previews": resultados}
