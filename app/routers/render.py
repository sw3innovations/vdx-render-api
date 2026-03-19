from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from app.models.render import RenderRequest, RenderResponse
from app.services.svg_service import gerar_svg
from app.services.claude_service import inferir_ferragens
from app.core.catalogo import (
    CATALOGO_LAYOUTS, FERRAGEM_DEFAULTS, normalizar_nome,
    resolver_layout_por_nome, aplicar_defaults_ferragem,
)

router = APIRouter(prefix="/api/v1", tags=["render"])


def _inferir_layout(request: RenderRequest) -> str:
    """Resolve o layout: usa o do request se não for 'auto', senão busca no catálogo."""
    if request.layout.value != "auto":
        return request.layout.value

    if request.tipologia_nome:
        encontrado = resolver_layout_por_nome(request.tipologia_nome)
        if encontrado:
            return encontrado

    # Fallback por nome das peças
    nomes = " ".join(p.nome.lower() for p in request.pecas)
    if "canto" in nomes or "l " in nomes:
        return "canto_l"
    if "bandeira" in nomes:
        return "bandeira_topo"
    if any(k in nomes for k in ["fixo", "movel", "móvel"]):
        return "fixo_movel_fixo"
    if any(k in nomes for k in ["basculante", "maxim", "guilhotina"]):
        return "basculante"
    if any(k in nomes for k in ["cobertura", "claraboia", "telhado"]):
        return "cobertura"
    if any(k in nomes for k in ["painel", "guarda", "sacada", "varanda"]):
        return "paineis_lineares"
    return "paralelas"


async def _enriquecer_ferragens(
    request: RenderRequest,
) -> tuple[list[list[dict]], bool]:
    """
    Para cada peça, enriquece as ferragens sem posição definida.
    Retorna (ferragens_por_peca, algum_claude_usado).
    """
    resultado: list[list[dict]] = []
    algum_claude = False

    for peca in request.pecas:
        sem_posicao = [
            f.model_dump() for f in peca.ferragens
            if f.posicao_y_mm is None
        ]
        com_posicao = [
            {**f.model_dump(), "inferida_por_ia": False}
            for f in peca.ferragens
            if f.posicao_y_mm is not None
        ]

        if sem_posicao:
            enriquecidas, claude = await inferir_ferragens(
                tipologia_nome=request.tipologia_nome,
                peca_nome=peca.nome,
                largura_mm=peca.largura_mm,
                altura_mm=peca.altura_mm,
                ferragens_sem_posicao=sem_posicao,
            )
            if claude:
                algum_claude = True
            resultado.append(com_posicao + enriquecidas)
        else:
            # Todas já têm posição → apenas converter para dict com flag
            resultado.append([{**f.model_dump(), "inferida_por_ia": False} for f in peca.ferragens])

    return resultado, algum_claude


@router.post("/render", response_model=RenderResponse)
async def render_endpoint(
    request: RenderRequest,
    x_vdx_key: Optional[str] = Header(None),
):
    if not x_vdx_key:
        raise HTTPException(status_code=401, detail="X-VDX-Key header obrigatório")

    layout = _inferir_layout(request)
    ferragens_enriquecidas, claude_usado = await _enriquecer_ferragens(request)

    pecas_dict = [p.model_dump() for p in request.pecas]
    svg = gerar_svg(
        pecas_input=pecas_dict,
        ferragens_por_peca=ferragens_enriquecidas,
        layout_usado=layout,
        opcoes_dict=request.opcoes.model_dump(),
        tipologia_nome=request.tipologia_nome,
        largura_px=request.opcoes.largura_px,
        altura_px=request.opcoes.altura_px,
    )

    alguma_inferida = any(
        f.get("inferida_por_ia", False)
        for lista in ferragens_enriquecidas
        for f in lista
    )

    return RenderResponse(
        svg=svg,
        largura_px=request.opcoes.largura_px,
        altura_px=request.opcoes.altura_px,
        layout_usado=layout,
        ferragens_inferidas=alguma_inferida,
        claude_usado=claude_usado,
    )
