from __future__ import annotations

from app.renderers.svg_renderer_v2 import (
    _ACABAMENTO, _VIDRO, VH, VW, MB, ML, MR, MT,
    _cota_h, _cota_v, _ferragens_svg, _gap_px, _line, _painel,
    _ind_correr, _ind_basculante, _ind_maxim,
)
from app.schemas.import_tipologia import PainelSchema, TipologiaImportadaSchema


# ─── Indicadores de abertura (local) ─────────────────────────────────────────

def _ind_abrir(gx: float, gy: float, gw: float, gh: float, borda: str, lado: str | None) -> str:
    """Arco de abertura com traçado pontilhado (stroke-dasharray='5 3')."""
    r = min(gw * 0.7, gh * 0.4)
    if lado in (None, "esquerda"):
        py = gy + gh / 2
        return (
            f'<path d="M {gx:.1f},{py - r:.1f} A {r:.1f},{r:.1f} 0 0,1 {gx:.1f},{py + r:.1f}"'
            f' fill="none" stroke="{borda}" stroke-width="1.2" stroke-dasharray="5 3"/>'
        )
    if lado == "direita":
        px, py = gx + gw, gy + gh / 2
        return (
            f'<path d="M {px:.1f},{py - r:.1f} A {r:.1f},{r:.1f} 0 0,0 {px:.1f},{py + r:.1f}"'
            f' fill="none" stroke="{borda}" stroke-width="1.2" stroke-dasharray="5 3"/>'
        )
    if lado == "topo":
        px = gx + gw / 2
        r = min(gh * 0.7, gw * 0.4)
        return (
            f'<path d="M {px - r:.1f},{gy:.1f} A {r:.1f},{r:.1f} 0 0,0 {px + r:.1f},{gy:.1f}"'
            f' fill="none" stroke="{borda}" stroke-width="1.2" stroke-dasharray="5 3"/>'
        )
    # base
    px, py = gx + gw / 2, gy + gh
    r = min(gh * 0.7, gw * 0.4)
    return (
        f'<path d="M {px - r:.1f},{py:.1f} A {r:.1f},{r:.1f} 0 0,1 {px + r:.1f},{py:.1f}"'
        f' fill="none" stroke="{borda}" stroke-width="1.2" stroke-dasharray="5 3"/>'
    )


def _ind_pivotante(gx: float, gy: float, gw: float, gh: float, borda: str) -> str:
    """Eixo pivô: linha vertical central tracejada."""
    cx = gx + gw / 2
    return _line(cx, gy, cx, gy + gh, borda, 1.5, "4 4")


# ─── Geometria de painéis ─────────────────────────────────────────────────────

def _build_panel_boxes_auto(
    paineis: list[PainelSchema],
    sc: float,
    area_w: float,
    area_h: float,
) -> list[tuple[float, float, float, float]]:
    """Painéis lado a lado horizontalmente (modo padrão)."""
    n = len(paineis)
    gap = _gap_px(n)
    total_gw = sum(p.largura_mm * sc for p in paineis) + gap * max(n - 1, 0)
    ox = ML + (area_w - total_gw) / 2
    boxes: list[tuple[float, float, float, float]] = []
    cur_x = ox
    for p in paineis:
        pw = p.largura_mm * sc
        ph = p.altura_mm * sc
        gy = MT + (area_h - ph) / 2
        boxes.append((cur_x, gy, pw, ph))
        cur_x += pw + gap
    return boxes


def _build_panel_boxes_explicit(
    paineis: list[PainelSchema],
    sc: float,
    ox: float,
    oy: float,
) -> list[tuple[float, float, float, float]]:
    """Painéis com coordenadas explícitas (posicao_x_mm / posicao_y_mm)."""
    return [
        (
            ox + (p.posicao_x_mm or 0.0) * sc,
            oy + (p.posicao_y_mm or 0.0) * sc,
            p.largura_mm * sc,
            p.altura_mm * sc,
        )
        for p in paineis
    ]


# ─── Render principal ─────────────────────────────────────────────────────────

def render_geometria_livre(tipologia: TipologiaImportadaSchema) -> str:
    """Renderiza tipologia de geometria livre como SVG de catálogo."""
    paineis = tipologia.paineis
    n = len(paineis)
    cor = tipologia.opcoes.cor.lower()
    acabamento = tipologia.opcoes.acabamento.lower()

    vidro_fill, vidro_borda = _VIDRO.get(cor, _VIDRO["incolor"])
    acab = _ACABAMENTO.get(acabamento, _ACABAMENTO["cromado"])

    area_w = VW - ML - MR
    area_h = VH - MT - MB

    use_explicit = any(p.posicao_x_mm is not None or p.posicao_y_mm is not None for p in paineis)

    if use_explicit:
        total_largura_mm = max((p.posicao_x_mm or 0.0) + p.largura_mm for p in paineis)
        total_altura_mm = max((p.posicao_y_mm or 0.0) + p.altura_mm for p in paineis)
        sc = min(area_w / total_largura_mm, area_h / total_altura_mm)
        ox = ML + (area_w - total_largura_mm * sc) / 2
        oy = MT + (area_h - total_altura_mm * sc) / 2
        panel_boxes = _build_panel_boxes_explicit(paineis, sc, ox, oy)
    else:
        total_largura_mm = sum(p.largura_mm for p in paineis)
        total_altura_mm = max(p.altura_mm for p in paineis)
        gap = _gap_px(n)
        sc = min(
            (area_w - gap * max(n - 1, 0)) / total_largura_mm,
            area_h / total_altura_mm,
        )
        panel_boxes = _build_panel_boxes_auto(paineis, sc, area_w, area_h)

    gx0 = panel_boxes[0][0]
    last_box = panel_boxes[-1]
    total_gw_px = last_box[0] + last_box[2] - gx0
    label_x = last_box[0] + last_box[2] + 8

    hatch_stroke = vidro_borda
    defs = (
        "  <defs>\n"
        f'    <pattern id="gh" patternUnits="userSpaceOnUse" width="10" height="10">\n'
        f'      <path d="M0,10 L10,0" stroke="{hatch_stroke}" stroke-width="0.45"'
        f' stroke-opacity="0.22"/>\n'
        f'    </pattern>\n'
        f'    <linearGradient id="vhl" x1="0" y1="0" x2="1" y2="0">\n'
        f'      <stop offset="0%" stop-color="white" stop-opacity="0.32"/>\n'
        f'      <stop offset="22%" stop-color="white" stop-opacity="0.0"/>\n'
        f'    </linearGradient>\n'
        f'  </defs>'
    )

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (f'<!-- VDX livre | {tipologia.nome}'
         f' | {total_largura_mm:.0f}x{total_altura_mm:.0f}mm | {cor} | {acabamento} -->'),
        (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VW} {VH}"'
         f' width="{VW}" height="{VH}">'),
        defs,
        f'  <rect width="{VW}" height="{VH}" fill="white"/>',
        '  <g id="desenho">',
    ]

    first_box = panel_boxes[0]
    parts.append(_cota_h(gx0, first_box[1], total_gw_px, total_largura_mm))
    parts.append(_cota_v(first_box[0], first_box[1], first_box[3], paineis[0].altura_mm))

    for idx, (painel, (gx, gy, gw, gh)) in enumerate(zip(paineis, panel_boxes)):
        parts.extend(_painel(gx, gy, gw, gh, vidro_fill, vidro_borda))

        if painel.abertura:
            ab = painel.abertura
            if ab.modo == "correr":
                parts.append(_ind_correr(gx, gy, gw, gh, vidro_borda))
            elif ab.modo == "basculante":
                parts.append(_ind_basculante(gx, gy, gw, gh, vidro_borda))
            elif ab.modo == "maxim_ar":
                parts.append(_ind_maxim(gx, gy, gw, gh, vidro_borda))
            elif ab.modo == "abrir":
                lado = ab.lado_dobradica or "esquerda"
                parts.append(_ind_abrir(gx, gy, gw, gh, vidro_borda, lado))
            elif ab.modo == "pivotante":
                parts.append(_ind_pivotante(gx, gy, gw, gh, vidro_borda))

        if painel.ferragens:
            ferragens_dict = [
                {
                    "tipo": f.tipo,
                    "codigo": f.codigo,
                    "nome": f.tipo,
                    "x_mm": f.x_mm,
                    "y_mm": f.y_mm,
                }
                for f in painel.ferragens
            ]
            lx = label_x if idx == n - 1 else None
            parts.append(_ferragens_svg(ferragens_dict, gx, gy, gw, gh, sc, acab, lx))

    parts.append("  </g>")
    parts.append("</svg>")
    return "\n".join(parts)
