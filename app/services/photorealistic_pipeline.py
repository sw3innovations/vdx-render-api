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
# Estilo vidraçaria brasileira: SEM MOLDURA, vidro temperado direto na parede,
# ferragens patch mínimas coladas no vidro, sem perfil de alumínio visível.
_PROMPTS: dict[str, str] = {
    "porta_pivotante_simples": (
        "photorealistic Brazilian-style frameless {cor} tempered glass pivot door, "
        "NO frame NO aluminum frame NO metal frame NO border, "
        "single glass panel installed directly in wall opening, "
        "two small {acab} patch pivot hinges attached directly to glass edge left side, "
        "slim vertical {acab} bar handle right side, concealed floor spring, "
        "8mm glass panel only, modern interior marble floor white walls, "
        "professional architectural photography, frameless glass no frame"
    ),
    "porta_pivotante_dupla_bandeira": (
        "photorealistic Brazilian-style frameless {cor} tempered glass double pivot door with fixed sidelites, "
        "NO frame NO aluminum frame NO metal frame, "
        "three frameless glass panels filling wall opening, pivot door center flanked by fixed panels, "
        "small {acab} patch pivot hinges on glass, slim {acab} bar handle, "
        "modern interior marble floor white walls, "
        "professional architectural photography, frameless glass no frame"
    ),
    "porta_abrir": (
        "photorealistic Brazilian-style frameless {cor} tempered glass swing door, "
        "NO frame NO aluminum frame NO metal frame NO border, "
        "single glass panel on glass-to-glass {acab} patch hinges left side, "
        "slim {acab} bar handle right side, no door frame glass only, "
        "8mm glass panel installed in wall opening, modern interior marble floor, "
        "professional architectural photography, frameless glass no frame"
    ),
    "porta_correr_2_folhas": (
        "photorealistic Brazilian-style frameless {cor} tempered glass 2-panel sliding door, "
        "NO frame NO aluminum frame NO metal frame, "
        "two glass panels sliding on minimal top-hung track recessed in ceiling, "
        "no visible frame, small {acab} patch finger pulls on glass, "
        "glass panels fill entire wall opening, modern interior, "
        "professional architectural photography, frameless sliding glass no frame"
    ),
    "porta_correr_3_folhas": (
        "photorealistic Brazilian-style frameless {cor} tempered glass 3-panel sliding door, "
        "NO frame NO aluminum frame NO metal frame, "
        "three glass panels on minimal recessed ceiling track, "
        "small {acab} patch pulls on glass, no visible frame or border, "
        "modern interior marble floor white walls, "
        "professional architectural photography, frameless sliding glass no frame"
    ),
    "porta_quatro_folhas": (
        "photorealistic Brazilian-style frameless {cor} tempered glass 4-panel sliding door, "
        "NO frame NO aluminum frame NO metal frame, "
        "four glass panels on double recessed ceiling track, "
        "small {acab} patch pulls, glass fills entire wall opening no visible frame, "
        "modern interior marble floor, "
        "professional architectural photography, frameless sliding glass no frame"
    ),
    "janela_correr_2_folhas": (
        "photorealistic Brazilian-style frameless {cor} tempered glass 2-panel sliding window, "
        "NO frame NO aluminum frame NO visible metal frame, "
        "two glass panels sliding on minimal {acab} bottom track recessed in sill, "
        "glass panels reach wall edges, minimal hardware, no border, "
        "modern interior white walls, "
        "professional architectural photography, frameless sliding glass window no frame"
    ),
    "janela_correr_2_folhas_oriun_plus": (
        "photorealistic Brazilian-style frameless {cor} tempered glass 2-panel sliding window Oriun Plus, "
        "NO frame NO aluminum frame NO visible border, "
        "ultra-slim {acab} bottom track only, glass panels fill opening, "
        "concealed hardware, glass-to-glass contact, modern interior white walls, "
        "professional architectural photography, frameless glass window no frame"
    ),
    "janela_quatro_folhas": (
        "photorealistic Brazilian-style frameless {cor} tempered glass 4-panel sliding window, "
        "NO frame NO aluminum frame NO metal frame, "
        "four glass panels on minimal double {acab} bottom track, "
        "glass fills entire opening no visible border, modern interior white walls, "
        "professional architectural photography, frameless sliding glass window no frame"
    ),
    "janela_quatro_folhas_orion_plus": (
        "photorealistic Brazilian-style frameless {cor} tempered glass 4-panel sliding window Orion Plus, "
        "NO frame NO aluminum frame NO visible border, "
        "ultra-slim {acab} track system, glass panels fill opening corner to corner, "
        "minimal hardware, modern interior white walls, "
        "professional architectural photography, frameless glass window no frame"
    ),
    "janela_3_folhas": (
        "photorealistic Brazilian-style frameless {cor} tempered glass 3-panel sliding window, "
        "NO frame NO aluminum frame NO metal border, "
        "three glass panels on minimal {acab} bottom track, "
        "no visible frame glass fills opening, modern interior white walls, "
        "professional architectural photography, frameless sliding glass window no frame"
    ),
    "janela_pivotante": (
        "photorealistic Brazilian-style frameless {cor} tempered glass pivot window, "
        "NO frame NO aluminum frame NO metal frame, "
        "single glass panel rotating on central {acab} pivot pin, "
        "glass mounted directly in wall opening no border, modern interior, "
        "professional architectural photography, frameless pivot glass window no frame"
    ),
    "janela_basculante": (
        "photorealistic Brazilian-style frameless {cor} tempered glass awning window, "
        "NO frame NO aluminum frame NO metal frame, "
        "single glass panel top-hinged on {acab} patch hinges, "
        "glass tilts outward no visible frame, modern interior white walls, "
        "professional architectural photography, frameless awning glass window no frame"
    ),
    "janela_maxim_ar": (
        "photorealistic Brazilian-style frameless {cor} tempered glass maxim-air window, "
        "NO frame NO aluminum frame NO metal frame, "
        "glass panel with {acab} friction stay arm, opens outward, "
        "no visible frame border, modern interior white walls, "
        "professional architectural photography, frameless glass window no frame"
    ),
    "box_frontal_2_folhas": (
        "photorealistic Brazilian-style frameless {cor} tempered glass shower enclosure 2 sliding panels, "
        "NO frame NO aluminum frame NO metal frame, "
        "two glass panels sliding on minimal {acab} bottom track, "
        "glass-to-wall seals only, no visible frame, white tile shower walls, "
        "professional architectural photography, frameless shower glass no frame"
    ),
    "box_canto_90": (
        "photorealistic Brazilian-style frameless {cor} tempered glass corner shower enclosure 90 degrees, "
        "NO frame NO aluminum frame NO metal frame, "
        "two glass panels meeting at corner with {acab} glass-to-glass hinge, "
        "no visible frame or border, white tile shower, "
        "professional architectural photography, frameless corner shower glass no frame"
    ),
    "box_articulado": (
        "photorealistic Brazilian-style frameless {cor} tempered glass bi-fold shower door, "
        "NO frame NO aluminum frame NO metal frame, "
        "two glass panels hinged together with {acab} glass-to-glass hinges, "
        "folds inward no visible frame, white tile shower walls, "
        "professional architectural photography, frameless bi-fold shower glass no frame"
    ),
    "box_de_giro": (
        "photorealistic Brazilian-style frameless {cor} tempered glass pivot shower door, "
        "NO frame NO aluminum frame NO metal frame, "
        "single glass panel on {acab} top-bottom pivot pins, "
        "rotates no visible frame or border, white tile shower, "
        "professional architectural photography, frameless pivot shower glass no frame"
    ),
    "box_flex": (
        "photorealistic Brazilian-style frameless {cor} tempered glass flexible shower enclosure, "
        "NO frame NO aluminum frame NO metal frame, "
        "glass panel on curved {acab} bottom track, "
        "no visible frame glass-to-wall seals, white tile shower, "
        "professional architectural photography, frameless shower glass no frame"
    ),
    "divisoria_porta_pivotante": (
        "photorealistic Brazilian-style frameless {cor} tempered glass office partition with pivot door, "
        "NO frame NO aluminum frame NO metal frame, "
        "floor-to-ceiling glass panels on {acab} patch fittings, "
        "pivot door integrated seamlessly no visible frame, modern office interior, "
        "professional architectural photography, frameless glass partition no frame"
    ),
    "guarda_corpo_linear": (
        "photorealistic Brazilian-style frameless {cor} tempered glass linear balustrade railing, "
        "NO frame NO aluminum frame NO visible top rail, "
        "glass panels in {acab} U-channel floor base only, "
        "glass rises from floor no top rail no border, modern interior marble floor, "
        "professional architectural photography, frameless glass balustrade no frame"
    ),
    "cobertura": (
        "photorealistic Brazilian-style frameless {cor} tempered glass overhead canopy, "
        "NO frame NO aluminum frame NO metal frame, "
        "structural glass panels on {acab} point-fixed spider fittings, "
        "glass ceiling no visible frame modern building exterior, "
        "professional architectural photography, frameless glass canopy no frame"
    ),
    "fechamento_de_sacada_6_folhas": (
        "photorealistic Brazilian-style frameless {cor} tempered glass 6-panel balcony enclosure, "
        "NO frame NO aluminum frame NO metal frame, "
        "six glass panels folding on {acab} glass-to-glass hinges, "
        "top minimal track glass fills balcony opening no visible frame, "
        "modern apartment exterior, "
        "professional architectural photography, frameless folding glass balcony no frame"
    ),
    "fachada_fixa": (
        "photorealistic Brazilian-style frameless {cor} tempered glass fixed facade panel, "
        "NO frame NO aluminum frame NO metal frame NO border, "
        "structural glass panel on {acab} spider point-fixed fittings, "
        "glass attached directly to building no visible frame, modern building exterior, "
        "professional architectural photography, frameless glass facade no frame"
    ),
    "vitrine": (
        "photorealistic Brazilian-style frameless {cor} tempered glass storefront vitrine, "
        "NO frame NO aluminum frame NO metal frame, "
        "floor-to-ceiling glass panels on {acab} patch hinges, "
        "glass door with patch lock no visible frame, modern retail interior, "
        "professional architectural photography, frameless glass storefront no frame"
    ),
    "balcão_de_pia_duas_folhas": (
        "photorealistic Brazilian-style frameless {cor} tempered glass 2-panel sliding cabinet doors, "
        "NO frame NO aluminum frame NO metal frame, "
        "two glass panels on minimal {acab} aluminum bottom track under counter, "
        "glass only no visible frame, modern bathroom vanity white cabinet, "
        "professional architectural photography, frameless glass cabinet doors no frame"
    ),
    "balcão_de_pia_quatro_folhas": (
        "photorealistic Brazilian-style frameless {cor} tempered glass 4-panel sliding cabinet doors, "
        "NO frame NO aluminum frame NO metal frame, "
        "four glass panels on double {acab} bottom track under counter, "
        "glass only no visible frame, modern bathroom vanity white cabinet, "
        "professional architectural photography, frameless glass cabinet doors no frame"
    ),
    "diâmetro": (
        "photorealistic Brazilian-style frameless {cor} tempered glass circular disc panel, "
        "NO frame NO aluminum frame NO metal border, "
        "round glass panel on {acab} point-fixed patch fittings, "
        "circular glass no frame no border, modern interior white wall, "
        "professional architectural photography, frameless circular glass no frame"
    ),
    "diâmetro_com_furo_no_meio": (
        "photorealistic Brazilian-style frameless {cor} tempered glass annular circular panel with center hole, "
        "NO frame NO aluminum frame NO metal border, "
        "ring-shaped glass on {acab} point-fixed patch fittings, "
        "no frame no border, modern interior white wall, "
        "professional architectural photography, frameless annular glass no frame"
    ),
}

_PROMPT_FALLBACK = (
    "photorealistic Brazilian-style frameless {cor} tempered glass panel, "
    "NO frame NO aluminum frame NO metal frame NO border, "
    "{acab} patch fittings attached directly to glass, "
    "glass only minimal hardware, modern interior white walls marble floor, "
    "professional architectural photography, frameless glass no frame"
)

# ── Modificadores de cor e acabamento ─────────────────────────────────────────
_COR_SUFFIX: dict[str, str] = {
    "incolor": "clear transparent",
    "verde": "green tinted",
    "fume": "smoke grey tinted",
    "fumê": "smoke grey tinted",
    "bronze": "bronze tinted",
    "azul": "blue tinted",
}

_ACABAMENTO_SUFFIX: dict[str, str] = {
    "cromado": "polished chrome",
    "inox": "brushed stainless steel",
    "dourado": "gold-plated",
    "preto": "matte black",
}

_COR_FALLBACK = "clear transparent"
_ACABAMENTO_FALLBACK = "polished chrome"


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
