"""
VDX Photorealistic Pipeline — SVG técnico → FLUX via Pollinations.ai

Pipeline primário:
  Pollinations.ai FLUX (gratuito, sem token, sem limite) → JPEG cache

Pipeline secundário (quando ZeroGPU disponível):
  SVG técnico → cairosvg PNG → cv2.Canny → HF Space FLUX+ControlNet → JPEG cache

Fallback final:
  CairoSVG PNG direto

Cache: disco em uploads/fotorrealistas/{chave}_{w}x{h}_{cor}_{acab}.jpg — permanente.
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

# ── Prompts por tipologia ──────────────────────────────────────────────────────
# Cada entrada descreve anatomia específica do produto em inglês técnico.
_PROMPTS: dict[str, str] = {
    "porta_pivotante_simples": (
        "professional product photography of a single frameless pivot glass door, "
        "point-fixed patch fittings, floor spring pivot mechanism, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "porta_pivotante_dupla_bandeira": (
        "professional product photography of a double-wing frameless pivot glass door "
        "with fixed sidelites, point-fixed patch fittings, floor spring pivot, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "porta_abrir": (
        "professional product photography of a frameless swing glass door, "
        "butt hinges with patch fittings, pull handle bar, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "porta_correr_2_folhas": (
        "professional product photography of a 2-panel frameless sliding glass door, "
        "top-hung track system, point-fixed patch fittings, recessed floor guide, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "porta_correr_3_folhas": (
        "professional product photography of a 3-panel frameless sliding glass door, "
        "top-hung track, patch fittings, soft-close mechanism, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "porta_quatro_folhas": (
        "professional product photography of a 4-panel frameless sliding glass door, "
        "top-hung double track, patch fittings, overlapping panels, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "janela_correr_2_folhas": (
        "professional product photography of a 2-panel frameless sliding glass window, "
        "aluminum track frame, stainless steel rollers, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "janela_correr_2_folhas_oriun_plus": (
        "professional product photography of a 2-panel sliding glass window Oriun Plus series, "
        "slim aluminum profile, concealed hardware, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "janela_quatro_folhas": (
        "professional product photography of a 4-panel frameless sliding glass window, "
        "double-track system, stainless rollers, flush handles, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "janela_quatro_folhas_orion_plus": (
        "professional product photography of a 4-panel sliding glass window Orion Plus series, "
        "ultra-slim aluminum profile, concealed hardware, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "janela_3_folhas": (
        "professional product photography of a 3-panel frameless sliding glass window, "
        "top-hung aluminum track, patch clips, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "janela_pivotante": (
        "professional product photography of a frameless pivot glass window, "
        "center-hung pivot bar, point-fixed fittings, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "janela_basculante": (
        "professional product photography of a frameless awning glass window, "
        "top-hinged patch fittings, friction stay arms, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "janela_maxim_ar": (
        "professional product photography of a maxim-air ventilating glass window, "
        "multi-point hinged opening, aluminum frame, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "box_frontal_2_folhas": (
        "professional product photography of a 2-panel frameless sliding shower enclosure, "
        "tempered glass panels, aluminum bottom track, chrome towel bar, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "box_canto_90": (
        "professional product photography of a corner 90-degree frameless shower enclosure, "
        "two tempered glass panels meeting at right angle, wall-mounted patch fittings, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "box_articulado": (
        "professional product photography of a bi-fold frameless shower door, "
        "articulated hinged tempered glass panels, wall-to-glass hinges, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "box_de_giro": (
        "professional product photography of a frameless pivot shower door, "
        "single tempered glass panel, floor-to-ceiling pivot pin, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "box_flex": (
        "professional product photography of a flex-track frameless shower enclosure, "
        "curved aluminum track, tempered glass panels, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "divisoria_porta_pivotante": (
        "professional product photography of a frameless glass office partition "
        "with integrated pivot door, point-fixed patch fittings, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "guarda_corpo_linear": (
        "professional product photography of a linear frameless glass balustrade railing, "
        "floor-mounted U-channel base, tempered glass panels, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "cobertura": (
        "professional product photography of a frameless glass canopy overhead cover, "
        "point-fixed patch fittings, structural tempered glass, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "fechamento_de_sacada_6_folhas": (
        "professional product photography of a 6-panel folding balcony glass enclosure, "
        "top-hung track, frameless tempered glass panels, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "fachada_fixa": (
        "professional product photography of a fixed frameless glass facade panel, "
        "structural point-fixed patch fittings, spider brackets, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "vitrine": (
        "professional product photography of a frameless storefront display glass vitrine, "
        "point-fixed patch fittings, hinged glass door, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "balcão_de_pia_duas_folhas": (
        "professional product photography of a under-counter cabinet with 2 sliding glass doors, "
        "frameless tempered glass, aluminum track, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "balcão_de_pia_quatro_folhas": (
        "professional product photography of a under-counter cabinet with 4 sliding glass doors, "
        "frameless tempered glass, double aluminum track, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "diâmetro": (
        "professional product photography of a circular frameless tempered glass disc panel, "
        "point-fixed patch fittings, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
    "diâmetro_com_furo_no_meio": (
        "professional product photography of a circular annular frameless tempered glass panel "
        "with center hole, point-fixed patch fittings, {cor}, {acab}, "
        "white studio background, soft diffused lighting, photorealistic, 4K, no people"
    ),
}

_PROMPT_FALLBACK = (
    "professional product photography of a frameless tempered glass door, "
    "point-fixed patch fittings, {cor}, {acab}, "
    "white studio background, soft diffused lighting, photorealistic, 4K, no people"
)

# ── Modificadores de cor e acabamento ─────────────────────────────────────────
_COR_SUFFIX: dict[str, str] = {
    "incolor": "clear transparent tempered glass",
    "verde": "green tinted tempered glass",
    "fume": "smoke grey tinted tempered glass",
    "fumê": "smoke grey tinted tempered glass",
    "bronze": "bronze tinted tempered glass",
    "azul": "blue tinted tempered glass",
}

_ACABAMENTO_SUFFIX: dict[str, str] = {
    "cromado": "polished chrome hardware and fittings",
    "inox": "brushed stainless steel hardware and fittings",
    "dourado": "gold-plated hardware and fittings",
    "preto": "matte black hardware and fittings",
}

_COR_FALLBACK = "clear transparent tempered glass"
_ACABAMENTO_FALLBACK = "polished chrome hardware and fittings"


# ── Cache ──────────────────────────────────────────────────────────────────────

def _cache_path(
    upload_dir: str,
    chave: str,
    largura: float,
    altura: float,
    cor: str = "incolor",
    acabamento: str = "cromado",
) -> Path:
    d = Path(upload_dir) / _CACHE_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    cor_safe = cor.replace("ê", "e").replace("â", "a")
    acab_safe = acabamento.replace("ê", "e")
    return d / f"{chave}_{int(largura)}x{int(altura)}_{cor_safe}_{acab_safe}.jpg"


# ── Prompt builder ─────────────────────────────────────────────────────────────

def _prompt_para_chave(
    chave: str,
    cor: str = "incolor",
    acabamento: str = "cromado",
) -> str:
    template = _PROMPTS.get(chave, _PROMPT_FALLBACK)
    cor_desc = _COR_SUFFIX.get(cor.lower(), _COR_FALLBACK)
    acab_desc = _ACABAMENTO_SUFFIX.get(acabamento.lower(), _ACABAMENTO_FALLBACK)
    return template.format(cor=cor_desc, acab=acab_desc)


# ── Backends ───────────────────────────────────────────────────────────────────

def _run_pollinations(
    chave: str,
    largura_mm: float,
    altura_mm: float,
    cor: str = "incolor",
    acabamento: str = "cromado",
) -> bytes:
    """Gera JPEG via Pollinations.ai FLUX (sem token, sem custo)."""
    import io
    from PIL import Image

    prompt = _prompt_para_chave(chave, cor, acabamento)
    encoded = urllib.parse.quote(prompt)
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


def _run_hf_canny(svg: str, cor: str = "incolor", acabamento: str = "cromado") -> bytes:
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
        cor_desc = _COR_SUFFIX.get(cor.lower(), _COR_FALLBACK)
        acab_desc = _ACABAMENTO_SUFFIX.get(acabamento.lower(), _ACABAMENTO_FALLBACK)
        prompt = (
            f"professional product photography frameless glass door, "
            f"{cor_desc}, {acab_desc}, white studio background, photorealistic"
        )
        token = settings.hf_token or None
        client = Client(_HF_SPACE, token=token, verbose=False)
        result = client.predict(
            prompt=prompt,
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


# ── Orquestrador público ───────────────────────────────────────────────────────

async def gerar_fotorrealista(
    svg: str,
    chave: str,
    largura_mm: float,
    altura_mm: float,
    upload_dir: str,
    cor: str = "incolor",
    acabamento: str = "cromado",
) -> tuple[bytes, str]:
    """
    Gera (ou retorna do cache) imagem fotorrealista.

    Ordem: Pollinations.ai FLUX → HF Canny Space → CairoSVG PNG

    Returns:
        (image_bytes, mime_type) — 'image/jpeg' ou 'image/png' no fallback final
    """
    cache = _cache_path(upload_dir, chave, largura_mm, altura_mm, cor, acabamento)
    if cache.exists():
        log.info("foto cache hit: %s", cache.name)
        return cache.read_bytes(), "image/jpeg"

    loop = asyncio.get_event_loop()

    # 1. Pollinations.ai (primário — R$0, sem token, FLUX)
    try:
        jpeg = await loop.run_in_executor(
            None, _run_pollinations, chave, largura_mm, altura_mm, cor, acabamento
        )
        cache.write_bytes(jpeg)
        log.info("foto via Pollinations cacheada: %s", cache.name)
        return jpeg, "image/jpeg"
    except Exception as exc:
        log.warning("Pollinations falhou (%s) — tentando HF Canny", exc)

    # 2. HF FLUX+ControlNet Canny (secundário — quando ZeroGPU disponível)
    try:
        jpeg = await loop.run_in_executor(None, _run_hf_canny, svg, cor, acabamento)
        cache.write_bytes(jpeg)
        log.info("foto via HF Canny cacheada: %s", cache.name)
        return jpeg, "image/jpeg"
    except Exception as exc:
        log.warning("HF Canny falhou (%s) — fallback PNG", exc)

    # 3. CairoSVG PNG técnico
    return _fallback_png(svg), "image/png"
