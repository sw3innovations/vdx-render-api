"""
VDX Conversion Service — converte SVG para PNG, PDF e thumbnail.
Dependências: cairosvg, Pillow, fpdf2.
"""
from __future__ import annotations

import io
import logging

log = logging.getLogger(__name__)


def svg_para_png(svg: str, scale: float = 2.0) -> bytes:
    """Converte SVG (string) → PNG (bytes).

    scale=2.0 → dobra a resolução (retina-ready).
    """
    import cairosvg
    return cairosvg.svg2png(bytestring=svg.encode("utf-8"), scale=scale)


def svg_para_pdf(svg: str) -> bytes:
    """Converte SVG (string) → PDF (bytes) via CairoSVG."""
    import cairosvg
    return cairosvg.svg2pdf(bytestring=svg.encode("utf-8"))


def svg_para_thumbnail(svg: str, largura: int = 240, altura: int = 180) -> bytes:
    """Converte SVG → PNG thumbnail (bytes) com Pillow para redimensionamento exato."""
    from PIL import Image

    png = svg_para_png(svg, scale=1.0)
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    img.thumbnail((largura, altura), Image.LANCZOS)

    # Fundo branco antes de salvar como PNG
    fundo = Image.new("RGBA", img.size, (255, 255, 255, 255))
    fundo.paste(img, mask=img.split()[3])

    out = io.BytesIO()
    fundo.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
