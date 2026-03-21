"""
Motor que consulta a Constitution para classificar peças,
posicionar ferragens e resolver kits.
Substitui posicionamento_service + classificador + kit_resolver como fonte de dados.
"""
import logging
from typing import Optional
from app.core import constitution
from app.core.normalizer import classificar_peca as _normalizer_classificar
from app.models.render import FerragemPosicionada, KitFerragem, RegrasInterativas

log = logging.getLogger(__name__)


def _eval_formula(formula: str, largura: float, altura: float) -> float:
    """Avalia fórmula de posição: 'altura - 50', 'largura * 0.50', '15', etc."""
    try:
        return float(eval(formula, {"__builtins__": {}},
                          {"altura": altura, "largura": largura}))
    except Exception:
        return 0.0


def classificar_peca(nome_peca: str, tipologia_dados: dict) -> str:
    """Classifica peça usando o Normalizador Inteligente (3 camadas)."""
    return _normalizer_classificar(nome_peca, tipologia_dados)


def posicionar_ferragens(
    peca_nome: str,
    largura_mm: float,
    altura_mm: float,
    tipologia_dados: dict,
    puxador: Optional[dict] = None,
) -> list[FerragemPosicionada]:
    """Posiciona ferragens usando fórmulas da Constitution."""
    classificacao = classificar_peca(peca_nome, tipologia_dados)
    if classificacao == "fixa":
        return []

    ferragens_config = tipologia_dados.get("ferragens_por_peca", {})
    config_list = ferragens_config.get(classificacao) or ferragens_config.get("movel") or []
    puxador_config = ferragens_config.get("puxador_config") or tipologia_dados.get("puxador_config")

    resultado = []

    for fc in config_list:
        y = _eval_formula(fc["y_formula"], largura_mm, altura_mm)
        x = _eval_formula(fc["x_formula"], largura_mm, altura_mm)
        y = max(20.0, min(y, altura_mm - 20.0))

        resultado.append(FerragemPosicionada(
            codigo=fc.get("codigo"),
            nome=fc["nome"],
            tipo=fc["tipo"],
            x_mm=round(x, 1),
            y_mm=round(y, 1),
            lado=fc["lado"],
            visual=fc["visual"],
            recorte=fc.get("recorte", "padrao_sm"),
        ))

    if puxador_config and puxador:
        _posicionar_puxador(resultado, puxador, puxador_config, largura_mm, altura_mm)
    elif puxador_config and not puxador:
        default = puxador_config.get("default")
        if default:
            y = _eval_formula(puxador_config["y_formula"], largura_mm, altura_mm)
            x = _eval_formula(puxador_config["x_formula"], largura_mm, altura_mm)
            resultado.append(FerragemPosicionada(
                codigo=default.get("codigo"),
                nome=default["nome"],
                tipo="puxador",
                x_mm=round(x, 1), y_mm=round(y, 1),
                lado=puxador_config["lado"],
                visual=default.get("visual", "circulo"),
                recorte="furo_passante",
            ))

    return resultado


def _posicionar_puxador(resultado, puxador, config, largura_mm, altura_mm):
    tipo = puxador.get("tipo_furacao", "")
    eixo = float(puxador.get("eixo_mm") or 0)
    center_y = _eval_formula(config["y_formula"], largura_mm, altura_mm)
    center_x = _eval_formula(config["x_formula"], largura_mm, altura_mm)
    lado = config["lado"]

    if config.get("aceita_eixo") and "EIXO" in tipo.upper() and eixo > 0:
        resultado.append(FerragemPosicionada(
            nome=f"Furo sup. (eixo {eixo:.0f}mm)", tipo="puxador",
            x_mm=round(center_x, 1), y_mm=round(center_y + eixo / 2, 1),
            lado=lado, visual="circulo", recorte="furo_passante"))
        resultado.append(FerragemPosicionada(
            nome=f"Furo inf. (eixo {eixo:.0f}mm)", tipo="puxador",
            x_mm=round(center_x, 1), y_mm=round(center_y - eixo / 2, 1),
            lado=lado, visual="circulo", recorte="furo_passante"))
    else:
        resultado.append(FerragemPosicionada(
            nome="Furo puxador", tipo="puxador",
            x_mm=round(center_x, 1), y_mm=round(center_y, 1),
            lado=lado, visual="circulo", recorte="furo_passante"))


def resolver_kit(tipologia_dados: dict) -> Optional[KitFerragem]:
    kit_data = tipologia_dados.get("kit")
    if not kit_data or kit_data.get("codigo") == "NENHUM":
        return None
    return KitFerragem(**kit_data)


def montar_regras_interativas(
    tipologia_dados: dict, largura_mm: float, altura_mm: float
) -> Optional[RegrasInterativas]:
    ferragens_config = tipologia_dados.get("ferragens_por_peca", {})
    puxador_config = (ferragens_config.get("puxador_config")
                      or tipologia_dados.get("puxador_config"))
    if not puxador_config:
        return None

    return RegrasInterativas(
        puxador_centro_y_mm=round(_eval_formula(puxador_config["y_formula"], largura_mm, altura_mm), 1),
        puxador_centro_x_mm=round(_eval_formula(puxador_config["x_formula"], largura_mm, altura_mm), 1),
    )
