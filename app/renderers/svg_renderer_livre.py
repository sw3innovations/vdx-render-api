from __future__ import annotations

from app.renderers.svg_renderer_v2 import (
    _ACABAMENTO, _VIDRO, VH, VW, MB, ML, MR, MT,
    _cota_h, _cota_v, _ferragens_svg, _gap_px, _painel,
)
from app.schemas.import_tipologia import TipologiaImportadaSchema


def render_geometria_livre(tipologia: TipologiaImportadaSchema) -> str:
    """Renderiza tipologia de geometria livre como SVG de catálogo."""
    paineis = tipologia.paineis
    n = len(paineis)
    cor = tipologia.opcoes.cor.lower()
    acabamento = tipologia.opcoes.acabamento.lower()

    vidro_fill, vidro_borda = _VIDRO.get(cor, _VIDRO["incolor"])
    acab = _ACABAMENTO.get(acabamento, _ACABAMENTO["cromado"])

    total_largura_mm = sum(p.largura_mm for p in paineis)
    total_altura_mm = max(p.altura_mm for p in paineis)

    area_w = VW - ML - MR
    area_h = VH - MT - MB
    gap = _gap_px(n)

    sc = min(
        (area_w - gap * max(n - 1, 0)) / total_largura_mm,
        area_h / total_altura_mm,
    )

    total_gw = sum(p.largura_mm * sc for p in paineis) + gap * max(n - 1, 0)
    ox = ML + (area_w - total_gw) / 2

    panel_boxes: list[tuple[float, float, float, float]] = []
    cur_x = ox
    for p in paineis:
        pw = p.largura_mm * sc
        ph = p.altura_mm * sc
        gy = MT + (area_h - ph) / 2
        panel_boxes.append((cur_x, gy, pw, ph))
        cur_x += pw + gap

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
