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


def _verificar_normas_abnt(body: RenderRequest, skill_chave: str) -> list[dict]:
    """
    Verificação determinística de normas ABNT.
    Fontes: NBR 7199:2016, NBR 14207:2009, NBR 14718:2019, NBR 16259:2014.

    Níveis:
      CRITICO — violação direta de norma (risco de acidente / processo)
      ALERTA  — fora da prática recomendada (risco técnico)
      INFO    — recomendação (não obrigatório mas indicado)
    """
    alertas = []
    tip = normalizar_nome(body.tipologia_nome) if body.tipologia_nome else ""
    esp = body.espessura_vidro_mm                       # None = não informado
    tv  = (body.tipo_vidro or "").strip().lower()       # "temperado"|"laminado"|"aramado"|"comum"|""

    def _a(nivel, norma, msg):
        alertas.append({"nivel": nivel, "norma": norma, "mensagem": msg})

    # ── 1. PORTAS ────────────────────────────────────────────────────────────────
    eh_porta = any(k in tip for k in ("porta", "pivotante", "correr_porta", "abrir"))
    if eh_porta:
        if tv in ("comum",):
            _a("CRITICO", "NBR 7199:2016",
               "Porta: vidro comum PROIBIDO. Use temperado ou laminado.")
        if esp is not None:
            if esp < 8:
                _a("CRITICO", "NBR 7199:2016",
                   f"Porta: espessura {esp:.0f}mm insuficiente. Mínimo 8mm (recomendado 10mm).")
            elif esp < 10:
                _a("ALERTA", "NBR 7199:2016",
                   f"Porta: espessura {esp:.0f}mm abaixo do recomendado de 10mm.")

    # ── 2. BOX BANHEIRO ──────────────────────────────────────────────────────────
    eh_box = any(k in tip for k in ("box", "banheiro"))
    if eh_box:
        if tv in ("comum",):
            _a("CRITICO", "NBR 14207:2009",
               "Box banheiro: vidro comum PROIBIDO. Obrigatório temperado ou laminado.")
        if esp is not None and esp < 8:
            nivel = "CRITICO" if esp < 6 else "ALERTA"
            _a(nivel, "NBR 14207:2009",
               f"Box banheiro: espessura {esp:.0f}mm — mínimo 8mm temperado. "
               "4mm permitido apenas encaixilhado ≤700×2000mm.")

    # ── 3. JANELAS ───────────────────────────────────────────────────────────────
    eh_janela = "janela" in tip
    if eh_janela:
        if esp is not None and esp < 6:
            _a("ALERTA", "NBR 7199:2016",
               f"Janela: espessura {esp:.0f}mm — recomendado mínimo 6mm temperado.")
        if esp is not None and esp <= 4:
            _a("ALERTA", "NBR 7199:2016",
               "Janela 4mm: permitido apenas encaixilhado nos 4 cantos e acima de 1100mm do piso.")

    # ── 4. GUARDA-CORPO ──────────────────────────────────────────────────────────
    eh_gc = "guarda_corpo" in skill_chave or any(k in tip for k in ("guarda_corpo", "guarda corpo"))
    if eh_gc:
        for peca in body.pecas:
            if peca.altura_mm < 1100:
                _a("CRITICO", "NBR 14718:2019",
                   f"Peça '{peca.nome}': altura {peca.altura_mm:.0f}mm abaixo do mínimo "
                   "de 1100mm exigido para guarda-corpo.")
        if tv and tv != "laminado":
            _a("CRITICO", "NBR 14718:2019 + NBR 7199:2016",
               f"Guarda-corpo: vidro '{tv}' PROIBIDO. Obrigatório vidro LAMINADO.")
        elif not tv:
            _a("INFO", "NBR 14718:2019",
               "Guarda-corpo: confirme que o vidro é LAMINADO (temperado simples é proibido).")
        if esp is not None and esp < 10:
            _a("ALERTA", "NBR 14718:2019",
               f"Guarda-corpo: espessura {esp:.0f}mm — recomendado mínimo 10mm laminado.")

    # ── 5. COBERTURA / CLARABOIA / MARQUISE ──────────────────────────────────────
    eh_cob = any(k in tip for k in ("cobertura", "claraboia", "telhado", "marquise"))
    if eh_cob:
        if tv not in ("laminado", "aramado"):
            nivel = "CRITICO" if tv in ("temperado", "comum") else "INFO"
            _a(nivel, "NBR 7199:2016",
               "Cobertura/claraboia: vidro temperado simples PROIBIDO. "
               "Obrigatório laminado ou aramado.")
        if esp is not None and esp < 8:
            _a("ALERTA", "NBR 7199:2016",
               f"Cobertura: espessura {esp:.0f}mm — recomendado mínimo 8mm laminado.")

    # ── 6. SACADA / FECHAMENTO DE VARANDA ────────────────────────────────────────
    eh_sacada = any(k in tip for k in ("sacada", "varanda", "fechamento_varanda"))
    if eh_sacada:
        if tv in ("comum",):
            _a("CRITICO", "NBR 16259:2014",
               "Sacada/varanda: vidro de segurança OBRIGATÓRIO. Vidro comum PROIBIDO.")
        if esp is not None and esp < 8:
            _a("ALERTA", "NBR 16259:2014",
               f"Sacada/varanda: espessura {esp:.0f}mm — recomendado mínimo 8mm.")

    # ── 7. DIVISÓRIA ─────────────────────────────────────────────────────────────
    eh_div = any(k in tip for k in ("divisoria", "divisória", "biombo"))
    if eh_div:
        if tv in ("comum",):
            _a("ALERTA", "NBR 7199:2016",
               "Divisória abaixo de 1100mm: vidro de segurança obrigatório.")
        if esp is not None and esp < 8:
            _a("ALERTA", "NBR 7199:2016",
               f"Divisória: espessura {esp:.0f}mm — recomendado mínimo 8mm temperado.")

    # ── 8. REGRA GERAL — 4mm PROIBIDO em aplicações críticas ─────────────────────
    if esp is not None and esp <= 4:
        apps_criticas = ("porta", "guarda_corpo", "cobertura", "sacada", "varanda", "marquise")
        if any(k in tip or k in skill_chave for k in apps_criticas):
            _a("CRITICO", "NBR 7199:2016",
               f"Vidro 4mm PROIBIDO para '{body.tipologia_nome or 'esta aplicação'}'. "
               "Permitido apenas em janelas encaixilhadas ou box encaixilhado ≤700×2000mm.")

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
