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
):  # public: browser <img src="...preview/png"> cannot send auth headers
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


# ─── Thumbnail 3D estático para catálogo ─────────────────────────────────────

def _default_pecas_para_thumbnail(chave: str):
    """Retorna lista de PecaInput com dimensões padrão para thumbnail do catálogo."""
    from app.models.render import PecaInput
    t = chave.lower()
    if any(k in t for k in ("guarda_corpo", "guarda-corpo", "guarda corpo")):
        return [PecaInput(nome="Painel", largura_mm=1500, altura_mm=1100)]
    if any(k in t for k in ("cobertura", "telhado", "pergola")):
        return [PecaInput(nome="Painel", largura_mm=1500, altura_mm=1000)]
    if any(k in t for k in ("janela",)):
        return [PecaInput(nome="Folha", largura_mm=600, altura_mm=1200),
                PecaInput(nome="Folha", largura_mm=600, altura_mm=1200)]
    if any(k in t for k in ("sacada", "varanda")):
        return [PecaInput(nome="Painel", largura_mm=3000, altura_mm=2100)]
    if any(k in t for k in ("duas_folhas", "2_folhas", "dupla")):
        return [PecaInput(nome="Folha E", largura_mm=450, altura_mm=2100),
                PecaInput(nome="Folha D", largura_mm=450, altura_mm=2100)]
    if any(k in t for k in ("quatro_folhas", "4_folhas", "quadrupla")):
        return [PecaInput(nome="F1", largura_mm=225, altura_mm=2100),
                PecaInput(nome="F2", largura_mm=225, altura_mm=2100),
                PecaInput(nome="F3", largura_mm=225, altura_mm=2100),
                PecaInput(nome="F4", largura_mm=225, altura_mm=2100)]
    # padrão: porta simples
    return [PecaInput(nome="Porta", largura_mm=900, altura_mm=2100)]


@router.get("/tipologia/{chave}/thumbnail/3d")
@limiter.limit("60/minute")
async def tipologia_thumbnail_3d(
    request: Request,
    chave: str,
):
    """Thumbnail PNG estático para uso no catálogo de tipologias. Público, sem auth."""
    from app.models.render import RenderRequest, Opcoes
    chave_norm, _ = normalizar_tipologia(chave)
    pecas = _default_pecas_para_thumbnail(chave_norm)
    body = RenderRequest(
        tipologia_nome=chave_norm,
        pecas=pecas,
        opcoes=Opcoes(largura_px=480, altura_px=360,
                      mostrar_cotas=False, mostrar_ferragens=False),
    )
    try:
        resultado = await executar(body, modo_svg="thumbnail")
    except Exception as e:
        log.error(f"Erro gerando thumbnail/3d para '{chave_norm}': {e}")
        raise HTTPException(status_code=500, detail=f"Falha ao gerar thumbnail: {e}")
    try:
        png = conversion_service.svg_para_png(resultado.svg, scale=1.0)
        media_type = "image/png"
        content = png
    except Exception:
        # SVG fallback caso CairoSVG não esteja disponível
        content = resultado.svg.encode()
        media_type = "image/svg+xml"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": f'inline; filename="{chave_norm}_3d_thumb.png"',
        },
    )

