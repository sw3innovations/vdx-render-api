"""
SVG Template Engine — gera desenhos técnicos de vidraçaria.

Recebe: List[PecaRenderizada] + dados opcionais de catálogo
Retorna: string SVG completa

Aprimora o svg_service.py com:
  - Símbolos de ferragem específicos por tipo (dobradiça, pivô, fechadura, puxador, roldana)
  - Recortes desenhados com geometria real (onda, retangular, furo_passante)
  - Cotas técnicas (largura embaixo, altura à esquerda)
  - Legenda de ferragens no rodapé
  - Templates de vidro por tipologia (porta, box, janela, basculante)

Sem dependências externas além da stdlib Python.
"""
from __future__ import annotations
import math
from typing import Optional


# ─── Constantes ───────────────────────────────────────────────────────────────

# Cores (tema técnico VDX)
COR_VIDRO_FILL    = "#EEF3FB"    # azul muito claro
COR_VIDRO_BORDA   = "#185FA5"    # azul técnico
COR_DIAGONAL      = "rgba(24,95,165,0.06)"
COR_FERRAGEM      = "#D85A30"    # laranja-ferrugem
COR_RECORTE       = "#E67E22"    # laranja recorte
COR_RECORTE_FILL  = "rgba(230,126,34,0.15)"
COR_COTA          = "#185FA5"    # azul cotas
COR_COTA_LINHA    = "#7F8C8D"    # cinza médio
COR_TEXTO         = "#1a3a8f"    # azul texto
COR_BG            = "#FFFFFF"

# Cores vidro em modo catálogo: (fill, stroke, highlight)
_VIDRO_COR_CATALOGO = {
    "incolor": ("rgba(190,220,235,0.28)", "#4A8EBB", "rgba(255,255,255,0.55)"),
    "verde":   ("rgba(74,122,91,0.42)",   "#2E7D52", "rgba(180,240,200,0.38)"),
    "fume":    ("rgba(70,70,70,0.52)",    "#444444", "rgba(160,160,160,0.28)"),
    "bronze":  ("rgba(139,105,20,0.46)",  "#8B6914", "rgba(240,195,110,0.32)"),
    "azul":    ("rgba(40,80,160,0.42)",   "#2860A0", "rgba(175,210,255,0.32)"),
}

# Cores ferragem por acabamento: (fill, stroke)
_FERRAGEM_COR_CATALOGO = {
    "cromado": ("#C8C8C8", "#909090"),
    "inox":    ("#A8A8A8", "#686868"),
    "dourado": ("#D4A843", "#B08830"),
    "preto":   ("#3C3C3C", "#181818"),
}

MARGIN_PX = 48     # margem em pixels ao redor do desenho


# ─── Primitivas SVG ───────────────────────────────────────────────────────────

def _r(v: float) -> str:
    """Formata float com 1 casa decimal."""
    return f"{v:.1f}"


def _rect(x, y, w, h, fill, stroke, sw=1.5, rx=0) -> str:
    return (f'<rect x="{_r(x)}" y="{_r(y)}" width="{_r(w)}" height="{_r(h)}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>')


def _line(x1, y1, x2, y2, stroke, sw=1.0, dash="") -> str:
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{_r(x1)}" y1="{_r(y1)}" x2="{_r(x2)}" y2="{_r(y2)}" '
            f'stroke="{stroke}" stroke-width="{sw}"{da}/>')


def _circle(cx, cy, r, fill, stroke, sw=1.5) -> str:
    return (f'<circle cx="{_r(cx)}" cy="{_r(cy)}" r="{_r(r)}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def _text(x, y, txt, fill, size=9, anchor="middle", weight="normal", rotate=0) -> str:
    rot = f' transform="rotate({rotate},{_r(x)},{_r(y)})"' if rotate else ""
    return (f'<text x="{_r(x)}" y="{_r(y)}" fill="{fill}" font-size="{size}" '
            f'font-family="\'Courier New\', monospace" text-anchor="{anchor}" '
            f'dominant-baseline="middle" font-weight="{weight}"{rot}>{txt}</text>')


def _arrow_h(x1, y1, x2, stroke, size=4) -> str:
    d = 1 if x2 > x1 else -1
    return (f'<line x1="{_r(x1)}" y1="{_r(y1)}" x2="{_r(x2)}" y2="{_r(y1)}" '
            f'stroke="{stroke}" stroke-width="1"/>'
            f'<polygon points="{_r(x2)},{_r(y1)} {_r(x2-d*size)},{_r(y1-size/2)} '
            f'{_r(x2-d*size)},{_r(y1+size/2)}" fill="{stroke}"/>')


def _arrow_v(x1, y1, y2, stroke, size=4) -> str:
    d = 1 if y2 > y1 else -1
    return (f'<line x1="{_r(x1)}" y1="{_r(y1)}" x2="{_r(x1)}" y2="{_r(y2)}" '
            f'stroke="{stroke}" stroke-width="1"/>'
            f'<polygon points="{_r(x1)},{_r(y2)} {_r(x1-size/2)},{_r(y2-d*size)} '
            f'{_r(x1+size/2)},{_r(y2-d*size)}" fill="{stroke}"/>')


# ─── Símbolos de ferragem ─────────────────────────────────────────────────────

def _simbolo_dobradica(px: float, py: float, sx: float, sy: float) -> str:
    """Retângulo pequeno + eixo de pivô."""
    rw, rh = max(6, sx * 0.03), max(14, sy * 0.025)
    ry = py - rh / 2
    parts = [
        f'<rect x="{_r(px)}" y="{_r(ry)}" width="{_r(rw)}" height="{_r(rh)}" '
        f'fill="{COR_FERRAGEM}" fill-opacity="0.3" stroke="{COR_FERRAGEM}" stroke-width="1.2"/>',
        _line(px + rw / 2, ry, px + rw / 2, ry + rh, COR_FERRAGEM, 0.8),
    ]
    return "\n".join(parts)


def _simbolo_pivo(px: float, py: float) -> str:
    """Círculo sólido."""
    r = 5
    return (_circle(px, py, r, COR_FERRAGEM, COR_FERRAGEM, 1)
            + "\n" + _circle(px, py, 2, COR_BG, COR_BG, 0))


def _simbolo_fechadura(px: float, py: float) -> str:
    """Retângulo com X interno."""
    rw, rh = 12, 18
    x0, y0 = px - rw / 2, py - rh / 2
    parts = [
        f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{rw}" height="{rh}" '
        f'fill="{COR_FERRAGEM}" fill-opacity="0.2" stroke="{COR_FERRAGEM}" stroke-width="1.2"/>',
        _line(x0, y0, x0 + rw, y0 + rh, COR_FERRAGEM, 0.8),
        _line(x0 + rw, y0, x0, y0 + rh, COR_FERRAGEM, 0.8),
    ]
    return "\n".join(parts)


def _simbolo_puxador(px: float, py: float) -> str:
    """Linha com círculos nas pontas (furo passante)."""
    r = 5
    return "\n".join([
        _circle(px, py, r, "none", COR_FERRAGEM, 1.5),
        _line(px - r, py, px + r, py, COR_FERRAGEM, 0.8),
        _line(px, py - r, px, py + r, COR_FERRAGEM, 0.8),
    ])


def _simbolo_roldana(px: float, py: float) -> str:
    """Círculo com eixo horizontal."""
    r = 6
    return "\n".join([
        _circle(px, py, r, "none", COR_FERRAGEM, 1.5),
        _line(px - r * 1.5, py, px + r * 1.5, py, COR_FERRAGEM, 1.0),
        _circle(px, py, 2, COR_FERRAGEM, COR_FERRAGEM, 0),
    ])


def _simbolo_trinco(px: float, py: float) -> str:
    """Retângulo pequeno com círculo central."""
    rw, rh = 14, 8
    x0, y0 = px - rw / 2, py - rh / 2
    return "\n".join([
        f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{rw}" height="{rh}" '
        f'fill="{COR_FERRAGEM}" fill-opacity="0.2" stroke="{COR_FERRAGEM}" stroke-width="1.2"/>',
        _circle(px, py, 2.5, COR_FERRAGEM, COR_FERRAGEM, 0),
    ])


def _simbolo_ferragem(tipo: str, px: float, py: float, sx: float, sy: float,
                      cor: str = COR_FERRAGEM) -> str:
    """Despacha para o símbolo correto pelo tipo."""
    t = tipo.lower()
    if "dobradica" in t or "dobradiça" in t:
        rw, rh = max(6, sx * 0.03), max(14, sy * 0.025)
        ry = py - rh / 2
        return (f'<rect x="{_r(px)}" y="{_r(ry)}" width="{_r(rw)}" height="{_r(rh)}" '
                f'fill="{cor}" fill-opacity="0.35" stroke="{cor}" stroke-width="1.2"/>\n'
                + _line(px + rw / 2, ry, px + rw / 2, ry + rh, cor, 0.8))
    if "pivo" in t or "pivô" in t:
        return (_circle(px, py, 5, cor, cor, 1)
                + "\n" + _circle(px, py, 2, COR_BG, COR_BG, 0))
    if "fechadura" in t or "fechamento" in t:
        rw, rh = 12, 18
        x0, y0 = px - rw / 2, py - rh / 2
        return (f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{rw}" height="{rh}" '
                f'fill="{cor}" fill-opacity="0.25" stroke="{cor}" stroke-width="1.2"/>\n'
                + _line(x0, y0, x0 + rw, y0 + rh, cor, 0.8)
                + "\n" + _line(x0 + rw, y0, x0, y0 + rh, cor, 0.8))
    if "puxador" in t:
        r = 5
        return "\n".join([_circle(px, py, r, "none", cor, 1.5),
                          _line(px - r, py, px + r, py, cor, 0.8),
                          _line(px, py - r, px, py + r, cor, 0.8)])
    if "roldana" in t:
        r = 6
        return "\n".join([_circle(px, py, r, "none", cor, 1.5),
                          _line(px - r * 1.5, py, px + r * 1.5, py, cor, 1.0),
                          _circle(px, py, 2, cor, cor, 0)])
    if "trinco" in t:
        rw, rh = 14, 8
        x0, y0 = px - rw / 2, py - rh / 2
        return "\n".join([
            f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{rw}" height="{rh}" '
            f'fill="{cor}" fill-opacity="0.25" stroke="{cor}" stroke-width="1.2"/>',
            _circle(px, py, 2.5, cor, cor, 0),
        ])
    # Genérico
    rw, rh = 10, 14
    x0, y0 = px - rw / 2, py - rh / 2
    return (f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{rw}" height="{rh}" '
            f'fill="{cor}" fill-opacity="0.25" stroke="{cor}" stroke-width="1.2"/>')


# ─── Recortes SVG ─────────────────────────────────────────────────────────────

def _recorte_furo(cx: float, cy: float, diametro_mm: float, sc: float) -> str:
    """Círculo de furo passante."""
    r = max(4, diametro_mm * sc / 2)
    return (f'<circle cx="{_r(cx)}" cy="{_r(cy)}" r="{_r(r)}" '
            f'fill="{COR_RECORTE_FILL}" stroke="{COR_RECORTE}" stroke-width="1.2" '
            f'stroke-dasharray="3 2"/>')


def _recorte_onda(cx: float, cy: float,
                  comprimento_mm: float, largura_mm: float,
                  furo_mm: Optional[float], sc: float) -> str:
    """
    Recorte tipo onda (dobradiça): retângulo vertical com furo central.
    Comprimento = dimensão vertical do rasgo; largura = profundidade no vidro.
    """
    rw = max(6, largura_mm * sc)   # profundidade (horizontal)
    rh = max(12, comprimento_mm * sc)  # comprimento (vertical)
    x0 = cx - rw / 2
    y0 = cy - rh / 2
    parts = [
        f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{_r(rw)}" height="{_r(rh)}" '
        f'fill="{COR_RECORTE_FILL}" stroke="{COR_RECORTE}" stroke-width="1.0" '
        f'stroke-dasharray="4 2" rx="2"/>',
    ]
    if furo_mm:
        r = max(3, furo_mm * sc / 2)
        parts.append(f'<circle cx="{_r(cx)}" cy="{_r(cy)}" r="{_r(r)}" '
                     f'fill="{COR_RECORTE_FILL}" stroke="{COR_RECORTE}" stroke-width="1.0"/>')
    return "\n".join(parts)


def _recorte_retangular(cx: float, cy: float,
                         comprimento_mm: float, largura_mm: float,
                         raio_mm: Optional[float], sc: float) -> str:
    """Recorte retangular / arredondado (fechadura, trinco)."""
    rw = max(8, comprimento_mm * sc)
    rh = max(6, largura_mm * sc)
    x0, y0 = cx - rw / 2, cy - rh / 2
    rx = max(0, (raio_mm or 0) * sc)
    return (f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{_r(rw)}" height="{_r(rh)}" '
            f'fill="{COR_RECORTE_FILL}" stroke="{COR_RECORTE}" stroke-width="1.2" '
            f'stroke-dasharray="4 2" rx="{_r(rx)}"/>')


def _recorte_svg(
    recorte_tipo: str,          # "padrao_sm" | "furo_passante" | "nenhum"
    recorte_catalogo: Optional[dict],  # dados reais do catálogo
    cx: float, cy: float,       # posição em canvas (px)
    sc: float,                  # escala mm → px
) -> str:
    """Desenha o recorte adequado na posição da ferragem."""
    if recorte_tipo == "nenhum":
        return ""

    # Se tiver dados do catálogo, usar geometria real
    if recorte_catalogo:
        tipo = recorte_catalogo.get("tipo", "furo_passante")
        comp = recorte_catalogo.get("comprimento_mm") or 0
        larg = recorte_catalogo.get("largura_mm") or 0
        furo = recorte_catalogo.get("furo_diametro_mm")
        raio = recorte_catalogo.get("raio_mm")

        if tipo == "furo_passante":
            return _recorte_furo(cx, cy, furo or 25, sc)
        if tipo == "onda":
            return _recorte_onda(cx, cy, comp or 110, larg or 27, furo, sc)
        if tipo in ("retangular", "retangular_arredondado"):
            return _recorte_retangular(cx, cy, comp or 73, larg or 45, raio, sc)

    # Fallback: usar tipo simplificado do blueprint
    if recorte_tipo == "furo_passante":
        return _recorte_furo(cx, cy, 25, sc)
    if recorte_tipo == "padrao_sm":
        # SM padrão = recorte tipo onda (dobradiça)
        return _recorte_onda(cx, cy, 110, 27, 25, sc)

    return ""


# ─── Cotas técnicas ───────────────────────────────────────────────────────────

def _cotas(px: float, py: float, pw: float, ph: float,
           largura_mm: float, altura_mm: float) -> str:
    """Desenha cotas de largura (acima) e altura (esquerda)."""
    parts = []
    # Cota horizontal — acima
    cy_c = py - 14
    parts += [
        _line(px, cy_c, px + pw, cy_c, COR_COTA_LINHA, 0.8),
        _line(px, py, px, cy_c, COR_COTA_LINHA, 0.8, "2 2"),
        _line(px + pw, py, px + pw, cy_c, COR_COTA_LINHA, 0.8, "2 2"),
        _arrow_h(px + 4, cy_c, px, COR_COTA_LINHA),
        _arrow_h(px + pw - 4, cy_c, px + pw, COR_COTA_LINHA),
        _text(px + pw / 2, cy_c - 7, f"{largura_mm:.0f}mm", COR_COTA, 8),
    ]
    # Cota vertical — esquerda
    cx_c = px - 14
    parts += [
        _line(cx_c, py, cx_c, py + ph, COR_COTA_LINHA, 0.8),
        _line(px, py, cx_c, py, COR_COTA_LINHA, 0.8, "2 2"),
        _line(px, py + ph, cx_c, py + ph, COR_COTA_LINHA, 0.8, "2 2"),
        _arrow_v(cx_c, py + 4, py, COR_COTA_LINHA),
        _arrow_v(cx_c, py + ph - 4, py + ph, COR_COTA_LINHA),
        _text(cx_c - 7, py + ph / 2, f"{altura_mm:.0f}mm", COR_COTA, 8, "middle", rotate=-90),
    ]
    return "\n".join(parts)


# ─── Vidro por tipologia ──────────────────────────────────────────────────────

def _vidro_base(px: float, py: float, pw: float, ph: float,
                tipologia: str = "") -> str:
    """Corpo do vidro: retângulo + diagonais + cantos técnicos."""
    parts = [
        _rect(px, py, pw, ph, COR_VIDRO_FILL, COR_VIDRO_BORDA, 1.5),
        _line(px, py, px + pw, py + ph, COR_DIAGONAL, 0.7),
        _line(px + pw, py, px, py + ph, COR_DIAGONAL, 0.7),
    ]
    # Cantos L técnicos
    cs = 10
    for cx_c, cy_c, dx, dy in [(px, py, 1, 1), (px + pw, py, -1, 1),
                                 (px, py + ph, 1, -1), (px + pw, py + ph, -1, -1)]:
        parts += [
            _line(cx_c, cy_c, cx_c + dx * cs, cy_c, COR_VIDRO_BORDA, 1.2),
            _line(cx_c, cy_c, cx_c, cy_c + dy * cs, COR_VIDRO_BORDA, 1.2),
        ]

    # Indicadores especiais por tipologia
    tip = tipologia.lower()
    if any(k in tip for k in ("correr", "deslizante", "sliding")):
        # Seta de deslizamento no centro
        cy = py + ph / 2
        mx = px + pw / 2
        aw = min(pw * 0.25, 20)
        parts += [
            _line(mx - aw, cy, mx + aw, cy, COR_FERRAGEM, 1.5),
            f'<polygon points="{_r(mx-aw)},{_r(cy)} {_r(mx-aw+6)},{_r(cy-4)} {_r(mx-aw+6)},{_r(cy+4)}" '
            f'fill="{COR_FERRAGEM}"/>',
            f'<polygon points="{_r(mx+aw)},{_r(cy)} {_r(mx+aw-6)},{_r(cy-4)} {_r(mx+aw-6)},{_r(cy+4)}" '
            f'fill="{COR_FERRAGEM}"/>',
        ]
    elif "basculante" in tip or "maxim" in tip:
        # Linha de abertura diagonal
        parts.append(_line(px, py + ph, px + pw, py, COR_COTA_LINHA, 0.8, "5 3"))

    return "\n".join(parts)



def _vidro_thumbnail(px: float, py: float, pw: float, ph: float) -> str:
    """Corpo do vidro em modo thumbnail: limpo, sem diagonais, com highlight."""
    parts = [
        _rect(px, py, pw, ph, "rgba(184,212,227,0.50)", "#185FA5", 1.5),
        _rect(px + 4, py + 6, max(pw * 0.08, 4), ph - 12,
              "rgba(255,255,255,0.45)", "none", 0),
    ]
    return "\n".join(parts)

def _vidro_catalogo(px: float, py: float, pw: float, ph: float,
                    cor: str = "incolor", acabamento: str = "cromado") -> str:
    """Corpo do vidro em modo catálogo: colorido, sem diagonais, com highlight."""
    cor_key = cor.lower().replace("ê", "e").replace("â", "a")
    vidro_fill, vidro_stroke, highlight = _VIDRO_COR_CATALOGO.get(
        cor_key, _VIDRO_COR_CATALOGO["incolor"]
    )
    hw = max(pw * 0.07, 5)
    parts = [
        _rect(px, py, pw, ph, vidro_fill, vidro_stroke, 2.0),
        (f'<rect x="{_r(px+3)}" y="{_r(py+6)}" width="{_r(hw)}" '
         f'height="{_r(ph-12)}" fill="{highlight}" rx="2"/>'),
    ]
    return "\n".join(parts)


# ─── Motor principal ──────────────────────────────────────────────────────────

class SVGTemplateEngine:
    """
    Motor de templates SVG para desenhos técnicos de vidraçaria.
    Aceita List[PecaRenderizada] (formato existente do pipeline).
    """

    def gerar_svg(
        self,
        pecas_renderizadas,             # List[PecaRenderizada]
        tipologia_nome: str = "",
        layout_usado: str = "paralelas",
        opcoes_dict: Optional[dict] = None,
        largura_px: int = 480,
        altura_px: int = 360,
        recortes_catalogo: Optional[dict] = None,  # {codigo_norm: {tipo, comp, larg, furo, raio}}
        modo: str = "tecnico",          # "tecnico" | "thumbnail" | "catalogo"
        cor: str = "incolor",
        acabamento: str = "cromado",
    ) -> str:
        """
        Gera SVG técnico de uma ou mais peças de vidraçaria.

        recortes_catalogo: mapeamento opcional de código normalizado para dados do catálogo.
            Usado para desenhar recortes com geometria real. Se None, usa fallback do blueprint.
        """
        if opcoes_dict is None:
            opcoes_dict = {}

        pecas = list(pecas_renderizadas)
        if not pecas:
            return self._svg_vazio(largura_px, altura_px)

        # ── Calcular escala ────────────────────────────────────────────────
        total_w_mm = sum(p.largura_mm for p in pecas)
        max_h_mm = max(p.altura_mm for p in pecas)

        is_thumbnail = (modo == "thumbnail")
        is_catalogo  = (modo == "catalogo")
        MARGIN_LOCAL = 24 if is_thumbnail else MARGIN_PX
        area_w = largura_px - 2 * MARGIN_LOCAL
        area_h = altura_px - 2 * MARGIN_LOCAL
        sx = area_w / total_w_mm if total_w_mm else 1.0
        sy = area_h / max_h_mm if max_h_mm else 1.0
        sc = min(sx, sy)
        ox = MARGIN_LOCAL + (area_w - total_w_mm * sc) / 2
        oy = MARGIN_LOCAL + (area_h - max_h_mm * sc) / 2

        # ── Renderizar peças ───────────────────────────────────────────────
        partes = []
        gap_px = max(sc * 5, 6)
        x_cur = ox

        mostrar_ferragens = opcoes_dict.get("mostrar_ferragens", not is_thumbnail)
        mostrar_cotas = opcoes_dict.get("mostrar_cotas", not is_thumbnail)
        mostrar_legenda = opcoes_dict.get("mostrar_legenda", not is_thumbnail and not is_catalogo)

        for peca in pecas:
            pw = peca.largura_mm * sc
            ph = peca.altura_mm * sc
            py = oy + (max_h_mm - peca.altura_mm) * sc  # alinhar pela base

            # Vidro
            if is_thumbnail:
                partes.append(_vidro_thumbnail(x_cur, py, pw, ph))
            elif is_catalogo:
                partes.append(_vidro_catalogo(x_cur, py, pw, ph, cor, acabamento))
            else:
                partes.append(_vidro_base(x_cur, py, pw, ph, tipologia_nome))

            # Nome da peça (omitido em thumbnail)
            if not is_thumbnail:
                partes.append(_text(x_cur + pw / 2, py + ph / 2, peca.nome,
                                     COR_TEXTO, 9, "middle", "bold"))

            # Cotas
            if mostrar_cotas:
                partes.append(_cotas(x_cur, py, pw, ph,
                                      peca.largura_mm, peca.altura_mm))

            # Ferragens e recortes
            if mostrar_ferragens:
                partes.append(self._ferragens_svg(
                    peca.ferragens, x_cur, py, pw, ph, sc,
                    tipologia_nome, recortes_catalogo or {},
                    acabamento=acabamento if is_catalogo else "cromado",
                ))

            x_cur += pw + gap_px

        # ── Legenda ────────────────────────────────────────────────────────
        legenda = "" if not mostrar_legenda else self._legenda(pecas, largura_px, altura_px)

        conteudo = "\n".join(partes) + ("\n" + legenda if legenda else "")

        bg_defs = ""
        bg_rect = f'  <rect width="{largura_px}" height="{altura_px}" fill="{COR_BG}"/>'
        if is_catalogo:
            bg_rect = (
                f'  <rect width="{largura_px}" height="{altura_px}" fill="#FFFFFF"/>\n'
                f'  <rect x="1" y="1" width="{largura_px-2}" height="{altura_px-2}" '
                f'fill="none" stroke="#CCCCCC" stroke-width="1"/>'
            )
        elif is_thumbnail:
            bg_defs = (
                f'  <defs>\n'
                f'    <linearGradient id="tn_bg" x1="0" y1="0" x2="0" y2="1">\n'
                f'      <stop offset="0%" stop-color="#F0F7FF"/>\n'
                f'      <stop offset="100%" stop-color="#D8EAF8"/>\n'
                f'    </linearGradient>\n'
                f'  </defs>\n'
            )
            bg_rect = f'  <rect width="{largura_px}" height="{altura_px}" fill="url(#tn_bg)"/>'
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<!-- VDX Template Engine | tipologia={tipologia_nome} | layout={layout_usado} -->\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {largura_px} {altura_px}" '
            f'width="{largura_px}" height="{altura_px}">\n'
            f'{bg_defs}'
            f'{bg_rect}\n'
            f'  <g id="desenho">\n{conteudo}\n  </g>\n'
            f'</svg>'
        )

    def _ferragens_svg(
        self,
        ferragens,                   # List[FerragemPosicionada]
        px: float, py: float,
        pw: float, ph: float,
        sc: float,
        tipologia: str,
        recortes_catalogo: dict,
        acabamento: str = "cromado",
    ) -> str:
        """Renderiza todas as ferragens + recortes de uma peça."""
        parts = []

        # Calcular posições canvas de cada ferragem
        posicoes = []
        for f in ferragens:
            # x_mm: distância da borda esquerda; y_mm: altura medida da base
            fx = px + f.x_mm * sc
            fy = py + ph - f.y_mm * sc
            # Clamp dentro da peça
            fx = max(px + 3, min(px + pw - 3, fx))
            fy = max(py + 3, min(py + ph - 3, fy))
            posicoes.append((fx, fy))

        # Anti-colisão de labels (empurra labels conflitantes para baixo)
        label_ys = [fy for _, fy in posicoes]
        min_gap = 16
        order = sorted(range(len(label_ys)), key=lambda i: label_ys[i])
        for _ in range(5):
            changed = False
            for k in range(1, len(order)):
                pi, ci = order[k - 1], order[k]
                if label_ys[ci] - label_ys[pi] < min_gap:
                    label_ys[ci] = label_ys[pi] + min_gap
                    changed = True
            if not changed:
                break
        label_ys = [max(py, min(py + ph, ly)) for ly in label_ys]

        label_x = px + pw + 6  # labels à direita da peça

        for i, f in enumerate(ferragens):
            fx, fy = posicoes[i]
            lfy = label_ys[i]

            # 1. Recorte (desenhado ANTES do símbolo, para ficar atrás)
            recorte_catalogo = recortes_catalogo.get(f.codigo)
            partes_recorte = _recorte_svg(f.recorte, recorte_catalogo, fx, fy, sc)
            if partes_recorte:
                parts.append(partes_recorte)

            # 2. Símbolo da ferragem
            _fcor_simb = _FERRAGEM_COR_CATALOGO.get(acabamento.lower(), (COR_FERRAGEM,))[0]
            parts.append(_simbolo_ferragem(f.tipo, fx, fy, pw, ph, cor=_fcor_simb))

            # 3. Label (nome à direita)
            nome_label = f.nome
            _fcors = _FERRAGEM_COR_CATALOGO.get(acabamento.lower(), (COR_FERRAGEM, COR_FERRAGEM))
            parts.append(_text(label_x, lfy, nome_label, _fcors[0], 8, "start"))

            # 4. Linha guia tracejada símbolo → label
            if abs(lfy - fy) > 4:
                _fcors2 = _FERRAGEM_COR_CATALOGO.get(acabamento.lower(), (COR_FERRAGEM, COR_FERRAGEM))
                parts.append(_line(fx + 8, fy, label_x - 2, lfy,
                                    _fcors2[0], 0.4, "2 2"))

        return "\n".join(parts)

    def _legenda(self, pecas, largura_px: int, altura_px: int) -> str:
        """Lista compacta de ferragens únicas no rodapé do SVG."""
        vistas = {}
        for peca in pecas:
            for f in peca.ferragens:
                chave = f.codigo or f.tipo
                if chave not in vistas:
                    vistas[chave] = f.nome

        if not vistas:
            return ""

        y_base = altura_px - 14
        x = 6
        parts = [_text(x, y_base, "Ferragens:", COR_TEXTO, 7, "start", "bold")]
        x += 58
        for cod, nome in list(vistas.items())[:8]:  # máx 8 na legenda
            label = f"{cod}: {nome}" if cod != nome else nome
            parts.append(_text(x, y_base, label, COR_COTA_LINHA, 7, "start"))
            x += min(len(label) * 5.5, 110)
            if x > largura_px - 20:
                break

        return "\n".join(parts)

    @staticmethod
    def _svg_vazio(largura_px: int, altura_px: int) -> str:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'viewBox="0 0 {largura_px} {altura_px}" '
                f'width="{largura_px}" height="{altura_px}">'
                f'<rect width="{largura_px}" height="{altura_px}" fill="{COR_BG}"/>'
                f'<text x="{largura_px//2}" y="{altura_px//2}" '
                f'text-anchor="middle" font-size="14" fill="{COR_COTA_LINHA}">'
                f'Sem peças para renderizar</text></svg>')
