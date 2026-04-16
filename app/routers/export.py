"""
Router de exportação — converte renders SVG para PNG, PDF e thumbnail.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from app.models.render import RenderRequest
from app.services.render_orchestrator import executar
from app.services import conversion_service
from app.core.normalizer import normalizar_tipologia
from app.services import preview_generator
from app.core.limiter import limiter
from app.core.auth import validate_api_key

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["export"])


# ─── Render + conversão imediata ─────────────────────────────────────────────

@router.post("/render/export/png")
@limiter.limit("5/second")
async def render_export_png(
    request: Request,
    body: RenderRequest,
    scale: float = Query(2.0, ge=0.5, le=4.0, description="Fator de escala (2.0 = retina)"),
    _auth: None = Depends(validate_api_key),
):
    """Gera desenho técnico e retorna diretamente como PNG."""
    resultado = await executar(body)
    try:
        png = conversion_service.svg_para_png(resultado.svg, scale=scale)
    except Exception as e:
        log.error(f"Erro na conversão SVG→PNG: {e}")
        raise HTTPException(status_code=500, detail=f"Falha na conversão PNG: {e}")
    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="render.png"'},
    )


@router.post("/render/export/pdf")
@limiter.limit("5/second")
async def render_export_pdf(
    request: Request,
    body: RenderRequest,
    _auth: None = Depends(validate_api_key),
):
    """Gera desenho técnico e retorna diretamente como PDF."""
    resultado = await executar(body)
    try:
        pdf = conversion_service.svg_para_pdf(resultado.svg)
    except Exception as e:
        log.error(f"Erro na conversão SVG→PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Falha na conversão PDF: {e}")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="render.pdf"'},
    )


@router.post("/render/export/thumbnail")
@limiter.limit("10/second")
async def render_export_thumbnail(
    request: Request,
    body: RenderRequest,
    largura: int = Query(240, ge=80, le=800),
    altura: int = Query(180, ge=60, le=600),
    _auth: None = Depends(validate_api_key),
):
    """Gera desenho técnico e retorna thumbnail PNG redimensionado."""
    resultado = await executar(body)
    try:
        thumb = conversion_service.svg_para_thumbnail(resultado.svg, largura, altura)
    except Exception as e:
        log.error(f"Erro gerando thumbnail: {e}")
        raise HTTPException(status_code=500, detail=f"Falha no thumbnail: {e}")
    return Response(
        content=thumb,
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="thumbnail.png"'},
    )


# ─── Preview de tipologia como PNG / thumbnail ────────────────────────────────

@router.get("/tipologia/{chave}/preview/png")
async def preview_tipologia_png(
    chave: str,
    scale: float = Query(2.0, ge=0.5, le=4.0),
    regenerar: bool = Query(False),
    _auth: None = Depends(validate_api_key),
):
    """Retorna o preview SVG da tipologia convertido para PNG."""
    chave_norm, dados = normalizar_tipologia(chave)
    if not dados:
        raise HTTPException(status_code=404, detail=f"Tipologia '{chave}' não encontrada")
    if regenerar:
        preview_generator.invalidar_cache(chave_norm)
    svg = await preview_generator.gerar_preview_async(chave_norm, dados)
    try:
        png = conversion_service.svg_para_png(svg, scale=scale)
    except Exception as e:
        log.error(f"Erro convertendo preview '{chave_norm}' para PNG: {e}")
        raise HTTPException(status_code=500, detail=f"Falha na conversão PNG: {e}")
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": f'inline; filename="{chave_norm}.png"',
        },
    )


@router.get("/tipologia/{chave}/preview/thumbnail")
async def preview_tipologia_thumbnail(
    chave: str,
    largura: int = Query(240, ge=80, le=800),
    altura: int = Query(180, ge=60, le=600),
    regenerar: bool = Query(False),
    _auth: None = Depends(validate_api_key),
):
    """Retorna thumbnail PNG do preview da tipologia."""
    chave_norm, dados = normalizar_tipologia(chave)
    if not dados:
        raise HTTPException(status_code=404, detail=f"Tipologia '{chave}' não encontrada")
    if regenerar:
        preview_generator.invalidar_cache(chave_norm)
    svg = await preview_generator.gerar_preview_async(chave_norm, dados)
    try:
        thumb = conversion_service.svg_para_thumbnail(svg, largura, altura)
    except Exception as e:
        log.error(f"Erro gerando thumbnail de '{chave_norm}': {e}")
        raise HTTPException(status_code=500, detail=f"Falha no thumbnail: {e}")
    return Response(
        content=thumb,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": f'inline; filename="{chave_norm}_thumb.png"',
        },
    )
