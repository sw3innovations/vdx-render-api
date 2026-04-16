"""
Motor que consulta a Constitution para classificar peças,
posicionar ferragens e resolver kits.
Substitui posicionamento_service + classificador + kit_resolver como fonte de dados.

Sprint 2: adicionada classe ConstitutionEngine que enriquece ferragens com dados
do catálogo (ferragens, recortes, equivalencias), mantendo as funções module-level
para compatibilidade com código existente.
"""
import logging
from typing import Optional
from app.core import constitution
from app.core.constitution import normalizar_formula
from app.core.normalizer import classificar_peca as _normalizer_classificar
from app.models.render import FerragemPosicionada, KitFerragem, RegrasInterativas

log = logging.getLogger(__name__)


def _eval_formula(formula: str, largura: float, altura: float) -> float:
    """Avalia fórmula de posição: 'altura - 50', 'largura * 0.50', '15', etc.

    Aplica normalizar_formula() antes do eval como camada defensiva,
    garantindo que fórmulas com variáveis em maiúsculas (LARGURA, ALTURA)
    sejam aceitas mesmo que tenham escapado da normalização no loader.
    Contrato VDX: variáveis de fórmula são SEMPRE minúsculas — normalizar_formula
    é a fonte da verdade; aplicar aqui é apenas defesa em profundidade.
    """
    formula_norm = normalizar_formula(formula)
    try:
        result = float(eval(formula_norm, {"__builtins__": {}},
                            {"altura": altura, "largura": largura,
                             "comprimento": largura, "espessura": 0.0,
                             "vano_l": largura, "vano_h": altura,
                             "a": largura, "b": altura, "x": 0.0, "y": 0.0}))
        if result == 0.0 and any(v in formula_norm for v in ("largura", "altura")):
            log.warning(
                f"_eval_formula: resultado 0.0 suspeito para '{formula}' "
                f"(largura={largura}, altura={altura}) — verificar fórmula"
            )
        return result
    except Exception as e:
        log.error(
            f"_eval_formula falhou para '{formula}' "
            f"(normalizada: '{formula_norm}', largura={largura}, altura={altura}): {e}"
        )
        raise ValueError(
            f"Fórmula inválida '{formula}': {e}"
        ) from e


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


# ─── Enriquecimento com catálogo ──────────────────────────────────────────────

def enriquecer_ferragem_com_catalogo(
    codigo_norm: str,
    fabricante: Optional[str] = None,
) -> dict:
    """
    Enriquece um blueprint de ferragem com dados físicos do catálogo.

    codigo_norm: código normalizado de 4 dígitos (ex: "1101", "1520")
    fabricante : preferência de fabricante ("HE", "AL", "SM") ou None

    Retorna dict com: codigo, material, dimensoes, recorte (primeiro do catálogo).
    Retorna {} se não encontrar dados de catálogo.
    """
    equivs = constitution.buscar_equivalentes(codigo_norm)
    if not equivs:
        return {}

    # Filtrar por fabricante preferido; se não especificado, usa o primeiro disponível
    if fabricante:
        por_fab = [e for e in equivs if e["fabricante_id"] == fabricante]
        codigo_real = por_fab[0]["codigo_fabricante"] if por_fab else None
    else:
        # Preferência: SM (inline / bem conhecida) → AL → HE
        _PREFERENCIA = ["SM", "AL", "HE"]
        codigo_real = None
        for fab_pref in _PREFERENCIA:
            match = [e for e in equivs if e["fabricante_id"] == fab_pref]
            if match:
                codigo_real = match[0]["codigo_fabricante"]
                break
        if not codigo_real:
            codigo_real = equivs[0]["codigo_fabricante"]

    if not codigo_real:
        return {}

    ferragem = constitution.buscar_ferragem(codigo_real)
    if not ferragem:
        return {}

    recortes = constitution.buscar_recortes(codigo_real)

    return {
        "codigo": codigo_real,
        "fabricante_id": ferragem.get("fabricante_id"),
        "material": ferragem.get("material"),
        "dimensoes": ferragem.get("dimensoes"),
        "recorte": recortes[0] if recortes else None,
    }


class ConstitutionEngine:
    """
    Interface orientada a objetos para o motor da Constitution.

    Combina os dois mundos de dados:
    - entries.dados → blueprint (ferragens_por_peca, fórmulas de posição)
    - ferragens/recortes/equivalencias → dados físicos do catálogo

    Mantém compatibilidade com as funções module-level para código legado.
    """

    def __init__(self):
        pass  # stateless — todas as queries vão direto ao DB via constitution.*

    def resolver_tipologia(
        self,
        tipologia_chave: str,
        largura_mm: float,
        altura_mm: float,
        peca_nome: str = "Folha Móvel",
        fabricante: Optional[str] = None,
        puxador: Optional[dict] = None,
        tipologia_dados: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        Resolve uma tipologia completa unindo blueprint e catálogo.

        Retorna dict com:
        {
            "tipologia": str,
            "largura": float, "altura": float,
            "classificacao": str,
            "ferragens": [
                {
                    "nome": str, "tipo": str,
                    "x": float, "y": float,          # posição em mm
                    "lado": str, "visual": str,
                    "codigo": str | None,             # do blueprint
                    "codigo_catalogo": str | None,    # do catálogo (fabricante)
                    "material": str | None,
                    "dimensoes": dict | None,
                    "recorte_tipo": str,             # do blueprint: "padrao_sm" | "furo_passante"
                    "recorte_catalogo": dict | None, # dados reais do catálogo
                }
            ],
            "fonte": "constitution+catalogo",
            "confianca": float,
        }
        """
        if tipologia_dados is None:
            entry = constitution.buscar(tipologia_chave, tipo="tipologia")
            if not entry:
                return None
            tipologia_dados = entry["dados"]
            confianca = entry["confianca"]
        else:
            confianca = tipologia_dados.get("_confianca", 0.9)

        classificacao = classificar_peca(peca_nome, tipologia_dados)
        ferragens_config = tipologia_dados.get("ferragens_por_peca", {})
        config_list = (ferragens_config.get(classificacao)
                       or ferragens_config.get("movel")
                       or [])

        ferragens_resolvidas = []

        for fc in config_list:
            y = _eval_formula(fc["y_formula"], largura_mm, altura_mm)
            x = _eval_formula(fc["x_formula"], largura_mm, altura_mm)
            y = max(20.0, min(y, altura_mm - 20.0))

            # Enriquecer com catálogo se tiver código de referência
            codigo_norm = fc.get("codigo")  # ex: "1101"
            catalogo = {}
            if codigo_norm:
                catalogo = enriquecer_ferragem_com_catalogo(codigo_norm, fabricante)

            ferragens_resolvidas.append({
                "nome":             fc["nome"],
                "tipo":             fc["tipo"],
                "x":                round(x, 1),
                "y":                round(y, 1),
                "lado":             fc["lado"],
                "visual":           fc["visual"],
                "codigo":           codigo_norm,
                "codigo_catalogo":  catalogo.get("codigo"),
                "material":         catalogo.get("material"),
                "dimensoes":        catalogo.get("dimensoes"),
                "recorte_tipo":     fc.get("recorte", "padrao_sm"),
                "recorte_catalogo": catalogo.get("recorte"),
            })

        # Puxador
        puxador_config = (ferragens_config.get("puxador_config")
                          or tipologia_dados.get("puxador_config"))
        if puxador_config:
            py = _eval_formula(puxador_config["y_formula"], largura_mm, altura_mm)
            px = _eval_formula(puxador_config["x_formula"], largura_mm, altura_mm)
            if puxador:
                eixo = float(puxador.get("eixo_mm") or 0)
                tipo_fur = puxador.get("tipo_furacao", "")
                if puxador_config.get("aceita_eixo") and "EIXO" in tipo_fur.upper() and eixo > 0:
                    for offset, sufixo in [(eixo / 2, "sup"), (-eixo / 2, "inf")]:
                        ferragens_resolvidas.append({
                            "nome": f"Furo {sufixo}. (eixo {eixo:.0f}mm)",
                            "tipo": "puxador", "x": round(px, 1),
                            "y": round(py + offset, 1),
                            "lado": puxador_config["lado"],
                            "visual": "circulo", "codigo": None,
                            "codigo_catalogo": None, "material": None,
                            "dimensoes": None, "recorte_tipo": "furo_passante",
                            "recorte_catalogo": None,
                        })
                else:
                    ferragens_resolvidas.append({
                        "nome": "Furo puxador", "tipo": "puxador",
                        "x": round(px, 1), "y": round(py, 1),
                        "lado": puxador_config["lado"],
                        "visual": "circulo", "codigo": None,
                        "codigo_catalogo": None, "material": None,
                        "dimensoes": None, "recorte_tipo": "furo_passante",
                        "recorte_catalogo": None,
                    })
            else:
                default = puxador_config.get("default")
                if default:
                    ferragens_resolvidas.append({
                        "nome": default.get("nome", "Puxador"),
                        "tipo": "puxador",
                        "x": round(px, 1), "y": round(py, 1),
                        "lado": puxador_config["lado"],
                        "visual": default.get("visual", "circulo"),
                        "codigo": default.get("codigo"),
                        "codigo_catalogo": None, "material": None,
                        "dimensoes": None, "recorte_tipo": "furo_passante",
                        "recorte_catalogo": None,
                    })

        return {
            "tipologia": tipologia_chave,
            "largura": largura_mm,
            "altura": altura_mm,
            "classificacao": classificacao,
            "ferragens": ferragens_resolvidas,
            "fonte": "constitution+catalogo",
            "confianca": confianca,
        }
