"""VisionService — Claude Vision para interpretar fotos e croquis de vãos.

Transforma imagens (foto de vão ou croqui) em especificações estruturadas
(tipologia sugerida, dimensões estimadas, tipo de abertura, notas técnicas).

Uso:
    svc = VisionService()
    if svc.disponivel:
        res = svc.analisar_foto_vao(image_base64, contexto="cozinha aberta")

Se ANTHROPIC_API_KEY ausente, `disponivel=False` e chamadas levantam RuntimeError.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import settings

log = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-20250514"
_MAX_TOKENS = 1500

_PROMPT_FOTO = """Você é o VDX Vision — engenheiro de vidraçaria analisando uma FOTO REAL de vão.

Analise a imagem e retorne APENAS um JSON (sem texto extra, sem markdown) com os campos:
{
  "tipologia_sugerida": "porta_pivotante_simples" | "porta_2_folhas" | "porta_3_folhas" | "porta_4_folhas" | "porta_6_folhas" | "box_banheiro" | "janela_maxim_ar" | "janela_basculante" | "guarda_corpo" | "fachada_fixa",
  "largura_mm": <int estimado>,
  "altura_mm": <int estimado>,
  "tipo_abertura": "pivotante" | "deslizante" | "basculante" | "fixo",
  "num_folhas": <int>,
  "espessura_vidro_mm": 8 | 10 | 12,
  "cor_vidro": "incolor" | "fume" | "verde" | "bronze" | "espelho",
  "observacoes": "<breve descrição técnica e pontos de atenção>",
  "confianca": 0.0-1.0
}

Contexto adicional do cliente: {CONTEXTO}

IMPORTANTE: Se não for possível estimar dimensões, use valores típicos da tipologia.
Retorne SOMENTE o JSON, nada mais."""

_PROMPT_CROQUI = """Você é o VDX Vision — engenheiro lendo um CROQUI/DESENHO A MÃO de projeto de vidraçaria.

Interprete o desenho e retorne APENAS um JSON (sem texto extra, sem markdown):
{
  "tipologia_sugerida": "<chave da tipologia>",
  "largura_mm": <int>,
  "altura_mm": <int>,
  "tipo_abertura": "pivotante" | "deslizante" | "basculante" | "fixo",
  "num_folhas": <int>,
  "espessura_vidro_mm": 8 | 10 | 12,
  "cor_vidro": "incolor" | "fume" | "verde" | "bronze" | "espelho",
  "observacoes": "<leitura técnica do croqui>",
  "confianca": 0.0-1.0
}

Notas do projetista: {NOTAS}

Priorize cotas escritas no desenho. Retorne SOMENTE o JSON."""


@dataclass
class VisionResult:
    """Resultado estruturado da análise Vision."""

    tipologia_sugerida: str
    largura_mm: int
    altura_mm: int
    tipo_abertura: str
    num_folhas: int
    espessura_vidro_mm: int
    cor_vidro: str
    observacoes: str
    confianca: float
    raw: dict[str, Any] = field(default_factory=dict)


class VisionService:
    """Wrapper do Claude Vision para foto/croqui → spec de projeto."""

    def __init__(self) -> None:
        self._client = None
        self._disponivel = False
        if settings.anthropic_api_key:
            try:
                import anthropic  # type: ignore
                self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                self._disponivel = True
            except Exception as e:
                log.warning("VisionService: falha ao instanciar cliente Anthropic: %s", e)
                self._disponivel = False

    @property
    def disponivel(self) -> bool:
        return self._disponivel

    # ── Public API ───────────────────────────────────────────────────────────

    def analisar_foto_vao(self, image_base64: str, contexto: str = "") -> VisionResult:
        """Analisa foto real de vão. Levanta RuntimeError se indisponível."""
        if not self._disponivel:
            raise RuntimeError("VisionService indisponível — ANTHROPIC_API_KEY não configurada")
        prompt = _PROMPT_FOTO.replace("{CONTEXTO}", contexto or "nenhum")
        log.info("VisionService.analisar_foto_vao: contexto_len=%d img_len=%d", len(contexto or ""), len(image_base64))
        return self._analisar(image_base64, prompt)

    def analisar_croqui(self, image_base64: str, notas: str = "") -> VisionResult:
        """Analisa croqui/desenho a mão. Levanta RuntimeError se indisponível."""
        if not self._disponivel:
            raise RuntimeError("VisionService indisponível — ANTHROPIC_API_KEY não configurada")
        prompt = _PROMPT_CROQUI.replace("{NOTAS}", notas or "nenhuma")
        log.info("VisionService.analisar_croqui: notas_len=%d img_len=%d", len(notas or ""), len(image_base64))
        return self._analisar(image_base64, prompt)

    # ── Internals ────────────────────────────────────────────────────────────

    def _analisar(self, image_base64: str, prompt: str) -> VisionResult:
        media_type = self._detect_media_type(image_base64)
        # Se veio data URL, strip prefix
        b64 = image_base64
        if "," in b64 and b64.lstrip().startswith("data:"):
            b64 = b64.split(",", 1)[1]

        msg = self._client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        raw_text = ""
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                raw_text += block.text
        log.info("VisionService: resposta raw_len=%d", len(raw_text))

        data = self._parse_json(raw_text)
        return self._to_result(data)

    @staticmethod
    def _detect_media_type(image_base64: str) -> str:
        """Detecta media type pelo header base64. Default image/jpeg."""
        b = image_base64.lstrip()
        if b.startswith("data:"):
            # data:image/png;base64,...
            try:
                return b.split(";", 1)[0].split(":", 1)[1]
            except Exception:
                return "image/jpeg"
        # Base64 puro: primeiros chars identificam o formato
        prefixes = {
            "iVBORw0KGgo": "image/png",
            "/9j/": "image/jpeg",
            "R0lGOD": "image/gif",
            "UklGR": "image/webp",
        }
        for pfx, mt in prefixes.items():
            if b.startswith(pfx):
                return mt
        return "image/jpeg"

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """Parse tolerante — remove fences ```json``` e tenta achar JSON no texto."""
        s = text.strip()
        # Fences
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL | re.IGNORECASE)
        if fence:
            s = fence.group(1)
        else:
            # Pega primeiro bloco { ... }
            m = re.search(r"\{.*\}", s, re.DOTALL)
            if m:
                s = m.group(0)
        try:
            return json.loads(s)
        except json.JSONDecodeError as e:
            log.warning("VisionService: JSON inválido — %s; raw=%r", e, text[:200])
            raise ValueError(f"Resposta Vision não é JSON válido: {e}") from e

    @staticmethod
    def _to_result(data: dict[str, Any]) -> VisionResult:
        def _i(key: str, default: int) -> int:
            try:
                return int(float(data.get(key, default)))
            except (TypeError, ValueError):
                return default

        def _s(key: str, default: str) -> str:
            v = data.get(key, default)
            return str(v) if v is not None else default

        def _f(key: str, default: float) -> float:
            try:
                return float(data.get(key, default))
            except (TypeError, ValueError):
                return default

        return VisionResult(
            tipologia_sugerida=_s("tipologia_sugerida", "porta_pivotante_simples"),
            largura_mm=_i("largura_mm", 900),
            altura_mm=_i("altura_mm", 2100),
            tipo_abertura=_s("tipo_abertura", "pivotante"),
            num_folhas=_i("num_folhas", 1),
            espessura_vidro_mm=_i("espessura_vidro_mm", 8),
            cor_vidro=_s("cor_vidro", "incolor"),
            observacoes=_s("observacoes", ""),
            confianca=max(0.0, min(1.0, _f("confianca", 0.5))),
            raw=data,
        )
