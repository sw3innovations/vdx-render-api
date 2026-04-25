"""
VDX Photorealistic Pipeline — SVG técnico → FLUX via Pollinations.ai

Pipeline primário:
  Pollinations.ai FLUX (gratuito, sem token, sem limite) → JPEG cache

Pipeline secundário (quando ZeroGPU disponível):
  SVG técnico → cairosvg PNG → cv2.Canny → HF Space FLUX+ControlNet → JPEG cache

Fallback final:
  CairoSVG PNG direto

Cache: disco em uploads/fotorrealistas/{chave}_{w}x{h}.jpg — permanente por dimensão.
Custo: R$0/mês.
"""
from __future__ import annotations

import asyncio
import logging
import urllib.parse
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

_CACHE_SUBDIR = "fotorrealistas"

_POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"
_HF_SPACE = "DamarJati/FLUX.1-DEV-Canny"
_HF_ENDPOINT = "/generate_image"

_PROMPT_TEMPLATE = (
    "professional product photography of a {tipo} glass door, "
    "frameless tempered glass, polished stainless steel hardware, "
    "white studio background, soft diffused lighting, photorealistic, 4K, no people"
)


def _cache_path(upload_dir: str, chave: str, largura: float, altura: float) -> Path:
    d = Path(upload_dir) / _CACHE_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{chave}_{int(largura)}x{int(altura)}.jpg"


def _prompt_para_chave(chave: str) -> str:
    tipo_map = {
        "porta": "pivot",
        "janela": "sliding window",
        "box": "shower enclosure",
        "vitrine": "storefront display",
        "divisoria": "partition",
    }
    chave_lower = chave.lower()
    tipo = next((v for k, v in tipo_map.items() if k in chave_lower), "pivot")
    return _PROMPT_TEMPLATE.format(tipo=tipo)


def _run_pollinations(chave: str, largura_mm: float, altura_mm: float) -> bytes:
    """Gera JPEG via Pollinations.ai FLUX (sem token, sem custo)."""
    import io
    from PIL import Image

    prompt = _prompt_para_chave(chave)
    encoded = urllib.parse.quote(prompt)
    # Proporção baseada nas dimensões reais (máx 1024px)
    aspect = largura_mm / altura_mm
    if aspect >= 1:
        w, h = 1024, max(512, int(1024 / aspect))
    else:
        w, h = max(512, int(1024 * aspect)), 1024
    url = f"{_POLLINATIONS_BASE}/{encoded}?width={w}&height={h}&seed=42&model=flux&nologo=true"

    req = urllib.request.Request(url, headers={"User-Agent": "VDX-Glass-Engine/2.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = resp.read()

    img = Image.open(io.BytesIO(data)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


def _run_hf_canny(svg: str) -> bytes:
    """Síncrono: SVG → Canny → HF FLUX ControlNet. Roda em executor."""
    import io
    import os
    import tempfile

    import cairosvg
    import cv2
    import numpy as np
    from gradio_client import Client
    from PIL import Image
    from app.config import settings

    # SVG → Canny
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=768, output_height=768)
    buf = np.frombuffer(png, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("cv2 falhou ao decodificar PNG")
    edges = cv2.Canny(cv2.GaussianBlur(img, (3, 3), 0), 50, 150)
    _, enc = cv2.imencode(".png", edges)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(enc.tobytes())
        tmp_path = tmp.name

    try:
        token = settings.hf_token or None
        client = Client(_HF_SPACE, token=token, verbose=False)
        result = client.predict(
            prompt="professional product photography glass door white background photorealistic",
            control_image=tmp_path,
            num_steps=28,
            guidance=4,
            width=1024,
            height=1024,
            seed=42,
            random_seed=False,
            api_name=_HF_ENDPOINT,
        )
        after_path = result[1]
        out = Image.open(after_path).convert("RGB")
        buf_out = io.BytesIO()
        out.save(buf_out, format="JPEG", quality=88, optimize=True)
        return buf_out.getvalue()
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
    Gera (ou retorna do cache) imagem fotorrealista.

    Ordem: Pollinations.ai FLUX → HF Canny Space → CairoSVG PNG

    Returns:
        (image_bytes, mime_type) — 'image/jpeg' ou 'image/png' no fallback final
    """
    cache = _cache_path(upload_dir, chave, largura_mm, altura_mm)
    if cache.exists():
        log.info("foto cache hit: %s", cache.name)
        return cache.read_bytes(), "image/jpeg"

    loop = asyncio.get_event_loop()

    # 1. Pollinations.ai (primário — R$0, sem token, FLUX)
    try:
        jpeg = await loop.run_in_executor(
            None, _run_pollinations, chave, largura_mm, altura_mm
        )
        cache.write_bytes(jpeg)
        log.info("foto via Pollinations cacheada: %s", cache.name)
        return jpeg, "image/jpeg"
    except Exception as exc:
        log.warning("Pollinations falhou (%s) — tentando HF Canny", exc)

    # 2. HF FLUX+ControlNet Canny (secundário — quando ZeroGPU disponível)
    try:
        jpeg = await loop.run_in_executor(None, _run_hf_canny, svg)
        cache.write_bytes(jpeg)
        log.info("foto via HF Canny cacheada: %s", cache.name)
        return jpeg, "image/jpeg"
    except Exception as exc:
        log.warning("HF Canny falhou (%s) — fallback PNG", exc)

    # 3. CairoSVG PNG técnico
    return _fallback_png(svg), "image/png"
