from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from app.models.render import RenderRequest, RenderResponse
from app.services.svg_service import gerar_svg
from app.services.claude_service import inferir_ferragens
from app.core.catalogo import (
    CATALOGO_LAYOUTS, FERRAGEM_DEFAULTS, normalizar_nome,
    resolver_layout_por_nome, aplicar_defaults_ferragem,
    inferir_ferragens_por_tipologia,
)
from app.core.skill_vidracaria import get_ferragens_para_peca, normalizar_para_skill

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


async def _enriquecer_ferragens(
    request: RenderRequest,
) -> tuple[list[list[dict]], bool, list[dict]]:
    """
    Para cada peça, enriquece as ferragens sem posição definida.
    Retorna (ferragens_por_peca, algum_claude_usado, alertas_norma).
    """
    resultado: list[list[dict]] = []
    algum_claude = False
    alertas: list[dict] = []

    skill_chave = normalizar_para_skill(request.tipologia_nome) if request.tipologia_nome else ""

    # Check ABNT determinista (roda sempre, independente do Claude)
    alertas.extend(_verificar_normas_abnt(request, skill_chave))

    for peca in request.pecas:
        # 1ª prioridade: skill de vidraçaria (determinista, posições calculadas)
        if not peca.ferragens and skill_chave:
            da_skill = get_ferragens_para_peca(
                skill_chave, peca.nome, peca.largura_mm, peca.altura_mm
            )
            if da_skill:
                resultado.append(da_skill)
                continue

        # 2ª prioridade: ferragens enviadas no request ou catálogo genérico
        ferragens_efetivas = peca.ferragens
        if not ferragens_efetivas and request.tipologia_nome:
            padrao = inferir_ferragens_por_tipologia(request.tipologia_nome)
            if padrao:
                from app.models.render import FerragemInput
                ferragens_efetivas = [FerragemInput(**f) for f in padrao]

        sem_posicao = [
            f.model_dump() for f in ferragens_efetivas
            if f.posicao_y_mm is None
        ]
        com_posicao = [
            {**f.model_dump(), "inferida_por_ia": False}
            for f in ferragens_efetivas
            if f.posicao_y_mm is not None
        ]

        if sem_posicao:
            # 3ª prioridade: Claude para posicionamento
            enriquecidas, claude, alertas_peca = await inferir_ferragens(
                tipologia_nome=request.tipologia_nome,
                peca_nome=peca.nome,
                largura_mm=peca.largura_mm,
                altura_mm=peca.altura_mm,
                ferragens_sem_posicao=sem_posicao,
            )
            if claude:
                algum_claude = True
            alertas.extend(alertas_peca)
            resultado.append(com_posicao + enriquecidas)
        else:
            resultado.append([{**f.model_dump(), "inferida_por_ia": False} for f in peca.ferragens])

    return resultado, algum_claude, alertas


@router.post("/render", response_model=RenderResponse)
async def render_endpoint(
    request: RenderRequest,
    x_vdx_key: Optional[str] = Header(None),
):
    if not x_vdx_key:
        raise HTTPException(status_code=401, detail="X-VDX-Key header obrigatório")

    layout = _inferir_layout(request)
    ferragens_enriquecidas, claude_usado, alertas_norma = await _enriquecer_ferragens(request)

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
        alertas_norma=alertas_norma,
    )
