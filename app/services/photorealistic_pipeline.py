"""
VDX Photorealistic Pipeline — SVG técnico → Canny → FLUX.1-DEV-Canny (HF ZeroGPU)

Pipeline:
  SVG técnico → cairosvg PNG → cv2.Canny → HF Space predict() → JPEG cache

Fallback:
  CairoSVG PNG direto se HF Space falhar

Cache: disco em uploads/fotorrealistas/{chave}_{w}x{h}.jpg — cache permanente por dimensão.
Custo: R$0/mês — HF Spaces público ZeroGPU.
"""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

_CACHE_SUBDIR = "fotorrealistas"
HF_SPACE = "DamarJati/FLUX.1-DEV-Canny"
HF_ENDPOINT = "/generate_image"

_FLUX_PROMPT = (
    "professional product photography of a glass door, frameless tempered glass, "
    "polished stainless steel hardware, studio white background, "
    "soft diffused lighting, photorealistic, 4K, sharp focus, no people"
)


def _cache_path(upload_dir: str, chave: str, largura: float, altura: float) -> Path:
    d = Path(upload_dir) / _CACHE_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{chave}_{int(largura)}x{int(altura)}.jpg"


def _svg_para_canny(svg: str, size: int = 768) -> bytes:
    """SVG → grayscale PNG → cv2.Canny edge map (white edges on black)."""
    import cairosvg
    import cv2
    import numpy as np

    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=size, output_height=size)
    buf = np.frombuffer(png, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("cv2 não decodificou PNG")
    blurred = cv2.GaussianBlur(img, (3, 3), 0)
    edges = cv2.Canny(blurred, threshold1=50, threshold2=150)
    _, out = cv2.imencode(".png", edges)
    return out.tobytes()


def _run_hf_pipeline(svg: str) -> bytes:
    """Síncrono: Canny → gradio_client → JPEG bytes. Roda em executor."""
    import io
    from gradio_client import Client
    from PIL import Image
    from app.config import settings

    canny_png = _svg_para_canny(svg, size=768)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(canny_png)
        tmp_path = tmp.name

    try:
        token = settings.hf_token or None
        client = Client(HF_SPACE, token=token, verbose=False)
        result = client.predict(
            prompt=_FLUX_PROMPT,
            control_image=tmp_path,
            num_steps=28,
            guidance=4,
            width=1024,
            height=1024,
            seed=42,
            random_seed=False,
            api_name=HF_ENDPOINT,
        )
        # result = (before_path, after_path) — gerado está em [1]
        after_path = result[1]
        img = Image.open(after_path).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=88, optimize=True)
        return buf.getvalue()
    finally:
        os.unlink(tmp_path)


def _fallback_png(svg: str) -> bytes:
    import cairosvg
    return cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=1024, output_height=1024)


async def gerar_fotorrealista(
    svg: str,
    chave: str,
    largura_mm: float,
    altura_mm: float,
    upload_dir: str,
) -> tuple[bytes, str]:
    """
    Gera (ou retorna do cache) imagem fotorrealista para a tipologia.

    Returns:
        (image_bytes, mime_type) — 'image/jpeg' ou 'image/png' no fallback
    """
    cache = _cache_path(upload_dir, chave, largura_mm, altura_mm)
    if cache.exists():
        log.info("foto cache hit: %s", cache.name)
        return cache.read_bytes(), "image/jpeg"

    try:
        loop = asyncio.get_event_loop()
        jpeg = await loop.run_in_executor(None, _run_hf_pipeline, svg)
        cache.write_bytes(jpeg)
        log.info("foto gerada e cacheada: %s", cache.name)
        return jpeg, "image/jpeg"
    except Exception as exc:
        log.warning("HF pipeline falhou (%s) — fallback PNG", exc)
        return _fallback_png(svg), "image/png"
