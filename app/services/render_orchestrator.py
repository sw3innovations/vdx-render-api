"""
Orquestrador do pipeline de render.
Toda lógica de negócio extraída de app/routers/render.py.

Conecta:
  normalização de tipologia → constitution engine → ABNT validator
  → SVG template engine → resposta

render.py fica apenas com concerns HTTP (auth, routing, serialização).
"""
import logging
from typing import Optional, List

from app.core.normalizer import normalizar_tipologia
from app.core.abnt_validator import ABNTValidator
from app.models.render import (
    RenderRequest, RenderResponse,
    PecaRenderizada, KitFerragem, RegrasInterativas, FerragemPosicionada,
)
from app.services import constitution_engine
from app.services.constitution_engine import ConstitutionEngine
from app.renderers.svg_template_engine import SVGTemplateEngine

log = logging.getLogger(__name__)

# Singletons — instanciados uma vez por processo
_abnt_validator = ABNTValidator()
_svg_engine = SVGTemplateEngine()
_ce = ConstitutionEngine()


def _inferir_layout(request: RenderRequest) -> str:
    """Resolve o layout: usa o do request se não for 'auto', senão infere pelo conteúdo."""
    if request.layout.value != "auto":
        return request.layout.value

    if request.tipologia_nome:
        # Importação local para não criar dependência circular
        try:
            from app._deprecated.catalogo import resolver_layout_por_nome
            encontrado = resolver_layout_por_nome(request.tipologia_nome)
            if encontrado:
                return encontrado
        except Exception:
            pass

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


async def executar(request: RenderRequest, modo_svg: str = "tecnico", cor: str = "incolor", acabamento: str = "cromado") -> RenderResponse:
    """
    Pipeline completo de render.

    Fluxo:
    1. Resolve layout
    2. Normaliza tipologia (Constitution → Claude Teacher → fallback)
    3. Posiciona ferragens + resolve kit + regras interativas
    4. Valida ABNT
    5. Gera SVG (template engine com enriquecimento de catálogo)
    6. Valida pós-render (async, para claude_inferido)
    7. Retorna RenderResponse
    """
    layout = _inferir_layout(request)
    tip_nome = request.tipologia_nome or ""

    # ── 1. Resolver tipologia ─────────────────────────────────────────────────
    chave, tipologia_dados = normalizar_tipologia(tip_nome) if tip_nome else ("", None)
    modo = "constitution" if tipologia_dados else None

    # Modo 2: Claude teacher
    if not tipologia_dados and tip_nome:
        from app.services import claude_teacher
        pecas_dicts = [{"nome": p.nome, "largura_mm": p.largura_mm,
                        "altura_mm": p.altura_mm} for p in request.pecas]
        tipologia_dados = await claude_teacher.resolver_tipologia_desconhecida(
            tip_nome, pecas_dicts)
        modo = "claude_inferido" if tipologia_dados else "fallback"

    skill_chave = chave or tip_nome.lower().replace(" ", "_")

    # ── 2. Montar peças renderizadas ──────────────────────────────────────────
    pecas_renderizadas: List[PecaRenderizada] = []
    recortes_catalogo: dict = {}     # {codigo_norm: recorte_dict} para o SVG engine

    for peca in request.pecas:
        puxador_dict = peca.puxador.model_dump() if peca.puxador else None

        if tipologia_dados:
            ferragens = constitution_engine.posicionar_ferragens(
                peca_nome=peca.nome,
                largura_mm=peca.largura_mm,
                altura_mm=peca.altura_mm,
                tipologia_dados=tipologia_dados,
                puxador=puxador_dict,
            )
            classificacao = constitution_engine.classificar_peca(peca.nome, tipologia_dados)

            # Enriquecer recortes com dados do catálogo (para SVG template engine)
            fabricante = getattr(request, "fabricante", None)
            for f in ferragens:
                if f.codigo and f.codigo not in recortes_catalogo:
                    try:
                        dados_cat = constitution_engine.enriquecer_ferragem_com_catalogo(
                            f.codigo, fabricante
                        )
                        if dados_cat.get("recorte"):
                            recortes_catalogo[f.codigo] = dados_cat["recorte"]
                    except Exception as e:
                        log.debug(f"Enriquecimento catálogo para '{f.codigo}' falhou: {e}")
        else:
            # Fallback: módulos legados
            from app._deprecated.posicionamento_service import posicionar_ferragens as _pos_legacy
            from app._deprecated.classificador import classificar_peca as _cls_legacy
            ferragens = _pos_legacy(
                peca_nome=peca.nome,
                largura_mm=peca.largura_mm,
                altura_mm=peca.altura_mm,
                tipologia_nome=tip_nome,
                puxador=puxador_dict,
            )
            classificacao = _cls_legacy(peca.nome, tip_nome)

        pecas_renderizadas.append(PecaRenderizada(
            nome=peca.nome,
            largura_mm=peca.largura_mm,
            altura_mm=peca.altura_mm,
            classificacao=classificacao,
            ferragens=ferragens,
        ))

    # ── 3. Kit ────────────────────────────────────────────────────────────────
    kit: Optional[KitFerragem] = None
    if tipologia_dados:
        kit = constitution_engine.resolver_kit(tipologia_dados)
    else:
        try:
            from app._deprecated.kit_resolver import resolver_kit as _kit_legacy
            kit_data = _kit_legacy(tip_nome)
            kit = KitFerragem(**kit_data) if kit_data else None
        except Exception:
            pass

    # ── 4. RegrasInterativas ──────────────────────────────────────────────────
    regras: Optional[RegrasInterativas] = None
    if tipologia_dados:
        for peca in request.pecas:
            cls = constitution_engine.classificar_peca(peca.nome, tipologia_dados)
            if cls in ("movel", "correr"):
                regras = constitution_engine.montar_regras_interativas(
                    tipologia_dados, peca.largura_mm, peca.altura_mm)
                break
    else:
        for pr in pecas_renderizadas:
            puxadores = [f for f in pr.ferragens if f.tipo == "puxador"]
            if puxadores:
                regras = RegrasInterativas(
                    puxador_centro_y_mm=pr.altura_mm * 0.50,
                    puxador_centro_x_mm=puxadores[0].x_mm,
                )
                break

    # ── 5. Validação ABNT ─────────────────────────────────────────────────────
    alturas = [p.altura_mm for p in request.pecas]
    alertas_norma = _abnt_validator.verificar(
        tipologia_nome=tip_nome,
        skill_chave=skill_chave,
        espessura_vidro_mm=request.espessura_vidro_mm,
        tipo_vidro=request.tipo_vidro,
        alturas_pecas=alturas,
    )

    # ── 6. SVG ────────────────────────────────────────────────────────────────
    opcoes_dict = request.opcoes.model_dump()
    try:
        svg = _svg_engine.gerar_svg(
            pecas_renderizadas=pecas_renderizadas,
            tipologia_nome=tip_nome,
            layout_usado=layout,
            opcoes_dict=opcoes_dict,
            largura_px=request.opcoes.largura_px,
            altura_px=request.opcoes.altura_px,
            recortes_catalogo=recortes_catalogo,
            modo=modo_svg,
            cor=cor,
            acabamento=acabamento,
        )
    except Exception as e:
        log.warning(f"SVGTemplateEngine falhou: {e} — usando svg_service fallback")
        from app.services.svg_service import gerar_svg as _gerar_svg_legacy
        svg = _gerar_svg_legacy(
            pecas_renderizadas=pecas_renderizadas,
            layout_usado=layout,
            opcoes_dict=opcoes_dict,
            tipologia_nome=tip_nome,
            largura_px=request.opcoes.largura_px,
            altura_px=request.opcoes.altura_px,
        )

    # ── 7. Validação pós-render (apenas claude_inferido, confiança < 0.95) ────
    if modo == "claude_inferido" and chave and tipologia_dados:
        try:
            from app.services import render_validator
            await render_validator.validar_posicionamento(
                tipologia_chave=chave,
                tipologia_nome=tip_nome,
                pecas=pecas_renderizadas,
                tipologia_dados=tipologia_dados,
            )
        except Exception as _ve:
            log.warning(f"Validação pós-render falhou silenciosamente: {_ve}")

    return RenderResponse(
        svg=svg,
        pecas=pecas_renderizadas,
        kit=kit,
        regras_interativas=regras,
        alertas_norma=alertas_norma,
        metadata={"layout_usado": layout, "tipologia_chave": chave, "modo": modo},
        largura_px=request.opcoes.largura_px,
        altura_px=request.opcoes.altura_px,
        layout_usado=layout,
        ferragens_inferidas=(modo == "claude_inferido"),
        claude_usado=(modo == "claude_inferido"),
    )
