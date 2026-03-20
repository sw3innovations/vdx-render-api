"""
Motor de posicionamento determinístico de ferragens — ZERO IA.
Regras de mercado brasileiro para vidraçaria temperada.

Coordenadas:
  x_mm = distância da borda ESQUERDA da peça
  y_mm = distância da BASE da peça (0 = base, altura_mm = topo)
"""

from typing import Optional, List
from app.models.render import FerragemPosicionada
from app.core.classificador import classificar_peca


def posicionar_ferragens(
    peca_nome: str,
    largura_mm: float,
    altura_mm: float,
    tipologia_nome: str,
    puxador: Optional[dict] = None,
) -> List[FerragemPosicionada]:
    """
    Posiciona ferragens com regras determinísticas de mercado.
    Peças fixas retornam lista vazia (nenhum furo).

    Regra fundamental:
      PORTA PIVOTANTE: dobradiças ESQUERDA, puxador+fechadura DIREITA
      BOX: dobradiças ESQUERDA, puxador botão CENTRO
      JANELA CORRER: roldanas na BASE, bate-fecha borda ESQUERDA
      BASCULANTE: trinco e suporte no CENTRO
    """
    classificacao = classificar_peca(peca_nome, tipologia_nome)
    if classificacao == "fixa":
        return []

    tip = tipologia_nome.strip().lower()
    resultado: List[FerragemPosicionada] = []

    eh_porta = any(k in tip for k in ("porta", "pivotante")) and "box" not in tip
    eh_box = "box" in tip
    eh_janela_correr = ("correr" in tip and "janela" in tip) or classificacao == "correr"
    eh_basculante = "basculante" in tip
    eh_maxim = "maxim" in tip

    if eh_porta:
        # PORTA PIVOTANTE
        resultado.append(FerragemPosicionada(
            codigo="1101", nome="Dobradiça Superior", tipo="dobradica",
            x_mm=15.0, y_mm=altura_mm - 50.0,
            lado="esquerdo", visual="retangulo", recorte="padrao_sm"))
        resultado.append(FerragemPosicionada(
            codigo="1103", nome="Dobradiça Inferior", tipo="dobradica",
            x_mm=15.0, y_mm=50.0,
            lado="esquerdo", visual="retangulo", recorte="padrao_sm"))
        resultado.append(FerragemPosicionada(
            codigo="1520", nome="Fechadura Central", tipo="fechadura",
            x_mm=largura_mm - 15.0, y_mm=altura_mm * 0.50,
            lado="direito", visual="retangulo", recorte="padrao_sm"))
        _adicionar_puxador(resultado, puxador, largura_mm, altura_mm,
                           x_default=largura_mm - 35.0, lado="direito")

    elif eh_box:
        # BOX BANHEIRO — peça PORTA
        resultado.append(FerragemPosicionada(
            codigo="1114", nome="Dobradiça Auto Superior", tipo="dobradica",
            x_mm=25.0, y_mm=altura_mm - 50.0,
            lado="esquerdo", visual="retangulo", recorte="padrao_sm"))
        resultado.append(FerragemPosicionada(
            codigo="1114", nome="Dobradiça Auto Inferior", tipo="dobradica",
            x_mm=25.0, y_mm=50.0,
            lado="esquerdo", visual="retangulo", recorte="padrao_sm"))
        if puxador:
            _adicionar_puxador(resultado, puxador, largura_mm, altura_mm,
                               x_default=largura_mm / 2.0, lado="centro")
        else:
            resultado.append(FerragemPosicionada(
                codigo="1504", nome="Puxador Botão", tipo="puxador",
                x_mm=largura_mm / 2.0, y_mm=altura_mm * 0.50,
                lado="centro", visual="circulo", recorte="furo_passante"))

    elif eh_janela_correr:
        # JANELA DE CORRER — peça MÓVEL
        resultado.append(FerragemPosicionada(
            codigo="1125", nome="Roldana", tipo="roldana",
            x_mm=50.0, y_mm=20.0,
            lado="esquerdo", visual="circulo", recorte="nenhum"))
        resultado.append(FerragemPosicionada(
            codigo="1125", nome="Roldana", tipo="roldana",
            x_mm=largura_mm - 50.0, y_mm=20.0,
            lado="direito", visual="circulo", recorte="nenhum"))
        resultado.append(FerragemPosicionada(
            codigo="1629B", nome="Bate-fecha", tipo="bate_fecha",
            x_mm=0.0, y_mm=altura_mm * 0.50,
            lado="esquerdo", visual="linha_h", recorte="nenhum"))

    elif eh_basculante:
        # JANELA BASCULANTE
        resultado.append(FerragemPosicionada(
            codigo="1335T", nome="Trinco Basculante", tipo="trinco",
            x_mm=largura_mm / 2.0, y_mm=altura_mm * 0.50,
            lado="centro", visual="retangulo", recorte="padrao_sm"))
        resultado.append(FerragemPosicionada(
            codigo="1500", nome="Suporte Abertura", tipo="suporte",
            x_mm=150.0, y_mm=altura_mm * 0.50,
            lado="esquerdo", visual="retangulo", recorte="nenhum"))

    elif eh_maxim:
        # JANELA MAXIM-AR
        resultado.append(FerragemPosicionada(
            codigo="1500", nome="Braço Articulado", tipo="suporte",
            x_mm=largura_mm * 0.30, y_mm=altura_mm - 30.0,
            lado="esquerdo", visual="retangulo", recorte="nenhum"))
        resultado.append(FerragemPosicionada(
            codigo="1500", nome="Braço Articulado", tipo="suporte",
            x_mm=largura_mm * 0.70, y_mm=altura_mm - 30.0,
            lado="direito", visual="retangulo", recorte="nenhum"))
        resultado.append(FerragemPosicionada(
            codigo="1335T", nome="Trinco", tipo="trinco",
            x_mm=largura_mm / 2.0, y_mm=altura_mm * 0.50,
            lado="centro", visual="retangulo", recorte="padrao_sm"))

    return resultado


def _adicionar_puxador(
    resultado: List[FerragemPosicionada],
    puxador: Optional[dict],
    largura_mm: float,
    altura_mm: float,
    x_default: float,
    lado: str,
) -> None:
    if not puxador:
        return
    tipo = puxador.get("tipo_furacao", "")
    eixo = float(puxador.get("eixo_mm") or 0)
    center_y = altura_mm * 0.50

    if "EIXO" in tipo.upper() and eixo > 0:
        resultado.append(FerragemPosicionada(
            nome=f"Furo sup. (eixo {eixo:.0f}mm)", tipo="puxador",
            x_mm=x_default, y_mm=center_y + eixo / 2.0,
            lado=lado, visual="circulo", recorte="furo_passante"))
        resultado.append(FerragemPosicionada(
            nome=f"Furo inf. (eixo {eixo:.0f}mm)", tipo="puxador",
            x_mm=x_default, y_mm=center_y - eixo / 2.0,
            lado=lado, visual="circulo", recorte="furo_passante"))
    else:
        resultado.append(FerragemPosicionada(
            nome="Furo puxador", tipo="puxador",
            x_mm=x_default, y_mm=center_y,
            lado=lado, visual="circulo", recorte="furo_passante"))
