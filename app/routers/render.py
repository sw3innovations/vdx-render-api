import os
import logging
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Request
from app.models.render import RenderRequest, RenderResponse
from app.services.svg_service import gerar_svg
from app.services.posicionamento_service import posicionar_ferragens
from app.core.catalogo import (
    CATALOGO_LAYOUTS, FERRAGEM_DEFAULTS, normalizar_nome,
    resolver_layout_por_nome, aplicar_defaults_ferragem,
    inferir_ferragens_por_tipologia,
)
from app.core.skill_vidracaria import get_ferragens_para_peca, normalizar_para_skill
from app.core.limiter import limiter

logger = logging.getLogger(__name__)

_VDX_API_KEY = os.getenv("VDX_API_MASTER_KEY", "")
if not _VDX_API_KEY:
    logger.warning("VDX_API_MASTER_KEY não configurada — modo dev, aceitando qualquer key")

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


def _verificar_normas_abnt(request: RenderRequest, skill_chave: str) -> list[dict]:
    """Check determinista de normas ABNT — roda independente do Claude."""
    from app.core.catalogo import normalizar_nome
    alertas = []
    tip = normalizar_nome(request.tipologia_nome) if request.tipologia_nome else ""

    if "guarda_corpo" in skill_chave or "guarda corpo" in tip:
        for peca in request.pecas:
            if peca.altura_mm < 1100:
                alertas.append({
                    "nivel": "CRITICO",
                    "norma": "NBR 14718:2019",
                    "mensagem": (
                        f"Peça '{peca.nome}': altura {peca.altura_mm:.0f}mm abaixo do mínimo "
                        f"de 1100mm exigido para guarda-corpo."
                    ),
                })
    if any(k in tip for k in ("cobertura", "claraboia", "telhado")):
        alertas.append({
            "nivel": "CRITICO",
            "norma": "NBR 7199:2016",
            "mensagem": "Cobertura: vidro temperado simples é PROIBIDO. Utilizar vidro laminado.",
        })
    return alertas


def _resolver_ferragens(body: RenderRequest) -> tuple[list[list[dict]], list[dict]]:
    """
    Resolve ferragens para cada peça usando posicionamento determinístico.
    Claude nunca é chamado. Retorna (ferragens_por_peca, alertas_norma).

    Pipeline por peça:
      1. Skill de vidraçaria → catálogo com posições calculadas (determinístico)
      2. Ferragens do request → posicionamento_service posiciona
      3. Catálogo genérico → posicionamento_service posiciona
      Em todos os casos: puxador explícito do frontend sobrepõe o da skill.
    """
    resultado: list[list[dict]] = []
    alertas: list[dict] = []

    skill_chave = normalizar_para_skill(body.tipologia_nome) if body.tipologia_nome else ""

    # Check ABNT determinista (roda sempre)
    alertas.extend(_verificar_normas_abnt(body, skill_chave))

    for peca in body.pecas:
        # Obter catálogo de ferragens (skill, request ou padrão)
        if not peca.ferragens and skill_chave:
            ferragens_lista = get_ferragens_para_peca(
                skill_chave, peca.nome, peca.largura_mm, peca.altura_mm
            ) or []
        else:
            ferragens_lista = [f.model_dump() for f in peca.ferragens]
            if not ferragens_lista and body.tipologia_nome:
                padrao = inferir_ferragens_por_tipologia(body.tipologia_nome)
                if padrao:
                    ferragens_lista = padrao

        puxador_dict = peca.puxador.model_dump() if peca.puxador else None

        posicionadas = posicionar_ferragens(
            peca_nome=peca.nome,
            largura_mm=peca.largura_mm,
            altura_mm=peca.altura_mm,
            ferragens=ferragens_lista,
            puxador=puxador_dict,
            tipologia_nome=body.tipologia_nome,
        )
        resultado.append(posicionadas)

    return resultado, alertas


@router.post("/render", response_model=RenderResponse)
@limiter.limit("10/second")
async def render_endpoint(
    request: Request,
    body: RenderRequest,
    x_vdx_key: Optional[str] = Header(None),
):
    if not x_vdx_key:
        raise HTTPException(status_code=401, detail="X-VDX-Key header obrigatório")
    if _VDX_API_KEY and x_vdx_key != _VDX_API_KEY:
        raise HTTPException(status_code=403, detail="X-VDX-Key inválida")

    layout = _inferir_layout(body)
    ferragens_enriquecidas, alertas_norma = _resolver_ferragens(body)
    claude_usado = False

    pecas_dict = [p.model_dump() for p in body.pecas]
    svg = gerar_svg(
        pecas_input=pecas_dict,
        ferragens_por_peca=ferragens_enriquecidas,
        layout_usado=layout,
        opcoes_dict=body.opcoes.model_dump(),
        tipologia_nome=body.tipologia_nome,
        largura_px=body.opcoes.largura_px,
        altura_px=body.opcoes.altura_px,
    )

    alguma_inferida = any(
        f.get("inferida_por_ia", False)
        for lista in ferragens_enriquecidas
        for f in lista
    )

    return RenderResponse(
        svg=svg,
        largura_px=body.opcoes.largura_px,
        altura_px=body.opcoes.altura_px,
        layout_usado=layout,
        ferragens_inferidas=alguma_inferida,
        claude_usado=claude_usado,
        alertas_norma=alertas_norma,
    )
