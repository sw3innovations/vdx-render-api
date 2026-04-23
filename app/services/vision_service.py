"""VisionService — dual-engine (Ollama local + Claude API fallback).

Transforma imagens (foto de vão ou croqui) em especificações estruturadas
(tipologia sugerida, dimensões estimadas, tipo de abertura, notas técnicas).

Estratégia:
  1. Tenta Ollama local (Gemma/Qwen com visão) — custo R$0
  2. Se Ollama indisponível ou falha, cai no Claude Vision API (fallback)
  3. Response inclui campo `engine` ("ollama_local" ou "claude_api")

Uso:
    svc = VisionService()
    if svc.disponivel:
        res = svc.analisar_foto_vao(image_base64, contexto="cozinha aberta")
        print(res.engine)  # "ollama_local" ou "claude_api"

`disponivel=True` se Ollama OU Claude estiverem acessíveis.
Chamadas levantam RuntimeError somente se AMBOS falharem.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import settings

log = logging.getLogger(__name__)

_CLAUDE_MODEL = "claude-sonnet-4-20250514"
_MAX_TOKENS = 1500

_OLLAMA_CHECK_CACHE_TTL = 60.0  # segundos

_PROMPT_FOTO_TMPL = """Você é o VDX Vision — engenheiro de vidraçaria analisando uma FOTO REAL de vão.

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

_PROMPT_CROQUI_TMPL = """Você é o VDX Vision — engenheiro lendo um CROQUI/DESENHO A MÃO de projeto de vidraçaria.

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
    engine: str = ""  # "ollama_local" | "claude_api" | ""


class VisionService:
    """Dual-engine: Ollama local primário + Claude API fallback."""

    def __init__(self) -> None:
        self._client = None
        self._claude_ok = False
        # Compat/override. Se setado explicitamente (True/False), sobrepõe a lógica dual.
        self._disponivel: Optional[bool] = None
        self._ollama_url = getattr(settings, "ollama_url", "http://localhost:11434").rstrip("/")
        self._ollama_model = getattr(settings, "ollama_vision_model", "gemma3")
        self._ollama_timeout = int(getattr(settings, "ollama_timeout_seconds", 60))
        # cache do status do Ollama
        self._ollama_cache_at: float = 0.0
        self._ollama_cache_value: bool = False

        if settings.anthropic_api_key:
            try:
                import anthropic  # type: ignore
                self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                self._claude_ok = True
            except Exception as e:
                log.warning("VisionService: falha ao instanciar cliente Anthropic: %s", e)
                self._claude_ok = False

    # ── Status ───────────────────────────────────────────────────────────────

    @property
    def disponivel(self) -> bool:
        """True se Ollama OU Claude estiverem disponíveis.

        Se `_disponivel` foi setado explicitamente (compat com testes antigos),
        respeita esse valor.
        """
        if self._disponivel is not None:
            return bool(self._disponivel)
        return self._claude_ok or self._check_ollama()

    def _check_ollama(self) -> bool:
        """Verifica se Ollama local está rodando e tem o modelo disponível.

        Cacheia resultado por 60s para evitar checagens excessivas.
        """
        now = time.time()
        if now - self._ollama_cache_at < _OLLAMA_CHECK_CACHE_TTL:
            return self._ollama_cache_value

        ok = False
        try:
            req = urllib.request.Request(f"{self._ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                data = json.loads(body)
                models = [m.get("name", "") for m in data.get("models", []) or []]
                # match exato ou pelo prefixo (ex: "gemma3" casa com "gemma3:latest")
                wanted = self._ollama_model
                ok = any(m == wanted or m.startswith(f"{wanted}:") for m in models)
                if not ok:
                    log.info(
                        "VisionService: Ollama up mas modelo '%s' não encontrado (disponíveis: %s)",
                        wanted, models,
                    )
        except Exception as e:
            log.debug("VisionService: Ollama indisponível: %s", e)
            ok = False

        self._ollama_cache_at = now
        self._ollama_cache_value = ok
        return ok

    # ── Public API ───────────────────────────────────────────────────────────

    def analisar_foto_vao(self, image_base64: str, contexto: str = "") -> VisionResult:
        """Analisa foto real de vão. Levanta RuntimeError se ambos engines indisponíveis."""
        prompt = self._build_prompt_foto(contexto)
        log.info(
            "VisionService.analisar_foto_vao: contexto_len=%d img_len=%d",
            len(contexto or ""), len(image_base64),
        )
        return self._analisar_dual(image_base64, prompt, tipo_input="foto")

    def analisar_croqui(self, image_base64: str, notas: str = "") -> VisionResult:
        """Analisa croqui/desenho a mão. Levanta RuntimeError se ambos engines indisponíveis."""
        prompt = self._build_prompt_croqui(notas)
        log.info(
            "VisionService.analisar_croqui: notas_len=%d img_len=%d",
            len(notas or ""), len(image_base64),
        )
        return self._analisar_dual(image_base64, prompt, tipo_input="croqui")

    # ── Prompts ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_prompt_foto(contexto: str) -> str:
        return _PROMPT_FOTO_TMPL.replace("{CONTEXTO}", contexto or "nenhum")

    @staticmethod
    def _build_prompt_croqui(notas: str) -> str:
        return _PROMPT_CROQUI_TMPL.replace("{NOTAS}", notas or "nenhuma")

    # ── Dual engine orchestration ────────────────────────────────────────────

    def _analisar_dual(self, image_base64: str, prompt: str, tipo_input: str) -> VisionResult:
        """Tenta Ollama local primeiro; se falhar, cai no Claude API."""
        # Respeita override explícito de _disponivel=False
        if self._disponivel is False:
            raise RuntimeError(
                "VisionService indisponível — nem Ollama local nem Claude API estão acessíveis"
            )

        # Normaliza data URL prefix
        b64 = image_base64
        if "," in b64 and b64.lstrip().startswith("data:"):
            b64 = b64.split(",", 1)[1]

        # 1) Ollama local
        if self._check_ollama():
            try:
                text = self._analisar_via_ollama(b64, prompt)
                result = self._parse_text_to_result(text, tipo_input)
                result.engine = "ollama_local"
                log.info("VisionService: engine=ollama_local OK")
                return result
            except Exception as e:
                log.warning(
                    "VisionService: Ollama falhou (%s) — fallback para Claude API", e,
                )

        # 2) Claude API fallback
        if self._claude_ok:
            text = self._analisar_via_claude(b64, prompt)
            result = self._parse_text_to_result(text, tipo_input)
            result.engine = "claude_api"
            log.info("VisionService: engine=claude_api OK")
            return result

        raise RuntimeError(
            "VisionService indisponível — nem Ollama local nem Claude API estão acessíveis"
        )

    # ── Ollama ───────────────────────────────────────────────────────────────

    def _analisar_via_ollama(self, image_b64: str, prompt: str) -> str:
        """Chama Ollama /api/generate com imagem base64. Retorna texto cru."""
        payload = json.dumps({
            "model": self._ollama_model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self._ollama_url}/api/generate",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self._ollama_timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        if "error" in data:
            raise RuntimeError(f"Ollama error: {data['error']}")
        text = data.get("response", "") or ""
        log.info("VisionService.ollama: resposta raw_len=%d", len(text))
        if not text.strip():
            raise RuntimeError("Ollama retornou resposta vazia")
        return text

    # ── Claude ───────────────────────────────────────────────────────────────

    def _analisar_via_claude(self, image_b64: str, prompt: str) -> str:
        """Chama Claude Vision API. Retorna texto cru concatenado dos blocks."""
        if self._client is None:
            raise RuntimeError("Claude client não inicializado")
        media_type = self._detect_media_type(image_b64)
        msg = self._client.messages.create(
            model=_CLAUDE_MODEL,
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
                                "data": image_b64,
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
        log.info("VisionService.claude: resposta raw_len=%d", len(raw_text))
        return raw_text

    # ── Parsing ──────────────────────────────────────────────────────────────

    def _parse_text_to_result(self, text: str, tipo_input: str) -> VisionResult:
        """Parseia texto cru (string) em VisionResult."""
        data = self._parse_json(text)
        return self._to_result(data)

    @staticmethod
    def _detect_media_type(image_base64: str) -> str:
        """Detecta media type pelo header base64. Default image/jpeg."""
        b = image_base64.lstrip()
        if b.startswith("data:"):
            try:
                return b.split(";", 1)[0].split(":", 1)[1]
            except Exception:
                return "image/jpeg"
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
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL | re.IGNORECASE)
        if fence:
            s = fence.group(1)
        else:
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
