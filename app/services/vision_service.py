"""VisionService — tri-engine (Moondream local + Gemma3 texto + Claude API fallback).

Transforma imagens (foto de vão ou croqui) OU descrições textuais em especificações
estruturadas (tipologia sugerida, dimensões estimadas, tipo de abertura, notas técnicas).

Engines:
  1. Moondream local (Ollama) — visão leve para imagens, CPU-friendly — R$0
  2. Gemma3 local (Ollama)   — interpretação de texto/chat, sem imagem — R$0
  3. Claude Vision API       — fallback para imagens se Moondream indisponível
  4. Claude Text API         — fallback para texto se Gemma3 indisponível

Métodos públicos:
  analisar_foto_vao(image_base64, contexto)  → visão (Moondream → Claude Vision)
  analisar_croqui(image_base64, notas)       → visão (Moondream → Claude Vision)
  analisar_descricao_texto(descricao, contexto) → texto (Gemma3 → Claude Text)

`disponivel=True` se Claude OU Moondream estiverem acessíveis (para imagens).
`disponivel_texto=True` se Claude OU Gemma3 estiverem acessíveis (para texto).
Chamadas levantam RuntimeError somente se todos os engines falharem.
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
# Timeout curto para visão no CPU — fail-fast para Claude se Moondream travar
_OLLAMA_VISION_TIMEOUT_CAP = 25  # 25s cap: fail-fast → Claude (25+25=50 < 60s nginx)
_OLLAMA_TEXT_TIMEOUT = 30          # 30s text cap: gemma3 slow on CPU (30+20=50 < 60s nginx)

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

_PROMPT_DESCRICAO_TMPL = """Você é o VDX Vision — especialista em vidraçaria interpretando uma DESCRIÇÃO VERBAL de projeto.

O cliente descreveu o seguinte projeto de vidraçaria:
"{DESCRICAO}"

Contexto adicional: {CONTEXTO}

Com base nesta descrição, identifique a tipologia e estimule as especificações técnicas.
Retorne APENAS um JSON (sem texto extra, sem markdown):
{
  "tipologia_sugerida": "porta_pivotante_simples" | "porta_2_folhas" | "porta_3_folhas" | "porta_4_folhas" | "porta_6_folhas" | "box_banheiro" | "janela_maxim_ar" | "janela_basculante" | "guarda_corpo" | "fachada_fixa",
  "largura_mm": <int estimado>,
  "altura_mm": <int estimado>,
  "tipo_abertura": "pivotante" | "deslizante" | "basculante" | "fixo",
  "num_folhas": <int>,
  "espessura_vidro_mm": 8 | 10 | 12,
  "cor_vidro": "incolor" | "fume" | "verde" | "bronze" | "espelho",
  "observacoes": "<interpretação técnica da descrição e valores assumidos>",
  "confianca": 0.0-1.0
}

Use valores padrão para campos não mencionados. Confiança deve ser menor se a descrição for vaga.
Retorne SOMENTE o JSON, nada mais."""


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
    engine: str = ""  # "moondream_local" | "gemma3_local" | "claude_api" | ""
    dimensoes_normalizadas: bool = False  # True when AI returned out-of-range dimensions


class VisionService:
    """Tri-engine: Moondream (visão) + Gemma3 (texto) + Claude API (fallback)."""

    def __init__(self) -> None:
        self._client = None
        self._claude_ok = False
        # Override explícito (True/False) sobrepõe a lógica tri-engine.
        self._disponivel: Optional[bool] = None
        self._ollama_url = getattr(settings, "ollama_url", "http://localhost:11434").rstrip("/")
        # Engine de visão: Moondream (leve, otimizado para CPU)
        self._ollama_vision_model = getattr(settings, "ollama_vision_model", "moondream")
        # Engine de texto: Gemma3 (sem imagem, mais rápido no CPU)
        self._ollama_text_model = getattr(settings, "ollama_text_model", "gemma3")
        # _ollama_model = alias para compatibilidade com testes que patcham diretamente
        self._ollama_model = self._ollama_vision_model
        self._ollama_timeout = int(getattr(settings, "ollama_timeout_seconds", 60))
        # Timeout de visão: cap em 60s para fail-fast → Claude
        self._ollama_vision_timeout = min(_OLLAMA_VISION_TIMEOUT_CAP, self._ollama_timeout)
        # Caches de status Ollama (visão e texto separados)
        self._ollama_cache_at: float = 0.0
        self._ollama_cache_value: bool = False
        self._ollama_text_cache_at: float = 0.0
        self._ollama_text_cache_value: bool = False

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
        """True se Claude Vision OU Moondream local estiverem disponíveis (para imagens)."""
        if self._disponivel is not None:
            return bool(self._disponivel)
        return self._claude_ok or self._check_ollama()

    @property
    def disponivel_texto(self) -> bool:
        """True se Claude OU Gemma3 local estiverem disponíveis (para texto)."""
        if self._disponivel is not None:
            return bool(self._disponivel)
        return self._claude_ok or self._check_ollama_text()

    def _check_ollama(self) -> bool:
        """Verifica se Ollama tem o modelo de VISÃO disponível. Cache 60s."""
        now = time.time()
        if now - self._ollama_cache_at < _OLLAMA_CHECK_CACHE_TTL:
            return self._ollama_cache_value

        ok = self._query_ollama_model(self._ollama_vision_model)
        self._ollama_cache_at = now
        self._ollama_cache_value = ok
        return ok

    def _check_ollama_text(self) -> bool:
        """Verifica se Ollama tem o modelo de TEXTO disponível. Cache 60s."""
        now = time.time()
        if now - self._ollama_text_cache_at < _OLLAMA_CHECK_CACHE_TTL:
            return self._ollama_text_cache_value

        ok = self._query_ollama_model(self._ollama_text_model)
        self._ollama_text_cache_at = now
        self._ollama_text_cache_value = ok
        return ok

    def _query_ollama_model(self, wanted: str) -> bool:
        """Consulta /api/tags e retorna True se `wanted` está na lista de modelos."""
        try:
            req = urllib.request.Request(f"{self._ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                data = json.loads(body)
                models = [m.get("name", "") for m in data.get("models", []) or []]
                ok = any(m == wanted or m.startswith(f"{wanted}:") for m in models)
                if not ok:
                    log.info(
                        "VisionService: Ollama up mas modelo '%s' não encontrado (disponíveis: %s)",
                        wanted, models,
                    )
                return ok
        except Exception as e:
            log.debug("VisionService: Ollama indisponível: %s", e)
            return False

    # ── Public API ───────────────────────────────────────────────────────────

    def analisar_foto_vao(self, image_base64: str, contexto: str = "") -> VisionResult:
        """Analisa foto real de vão. Engines: Moondream → Claude Vision."""
        prompt = self._build_prompt_foto(contexto)
        log.info(
            "VisionService.analisar_foto_vao: contexto_len=%d img_len=%d",
            len(contexto or ""), len(image_base64),
        )
        return self._analisar_dual(image_base64, prompt, tipo_input="foto")

    def analisar_croqui(self, image_base64: str, notas: str = "") -> VisionResult:
        """Analisa croqui/desenho a mão. Engines: Moondream → Claude Vision."""
        prompt = self._build_prompt_croqui(notas)
        log.info(
            "VisionService.analisar_croqui: notas_len=%d img_len=%d",
            len(notas or ""), len(image_base64),
        )
        return self._analisar_dual(image_base64, prompt, tipo_input="croqui")

    def analisar_descricao_texto(
        self, descricao: str, contexto: str = ""
    ) -> VisionResult:
        """Interpreta descrição verbal do projeto. Engines: Gemma3 → Claude Text.

        Não requer imagem — ideal para chatbot onde o cliente descreve verbalmente o vão.
        Levanta RuntimeError se ambos engines indisponíveis.
        """
        prompt = self._build_prompt_descricao(descricao, contexto)
        log.info(
            "VisionService.analisar_descricao_texto: descricao_len=%d",
            len(descricao or ""),
        )
        return self._analisar_dual_texto(prompt)

    # ── Prompts ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_prompt_foto(contexto: str) -> str:
        return _PROMPT_FOTO_TMPL.replace("{CONTEXTO}", contexto or "nenhum")

    @staticmethod
    def _build_prompt_croqui(notas: str) -> str:
        return _PROMPT_CROQUI_TMPL.replace("{NOTAS}", notas or "nenhuma")

    @staticmethod
    def _build_prompt_descricao(descricao: str, contexto: str) -> str:
        return (
            _PROMPT_DESCRICAO_TMPL
            .replace("{DESCRICAO}", descricao or "")
            .replace("{CONTEXTO}", contexto or "nenhum")
        )

    # ── Dual engine orchestration — visão (imagem) ───────────────────────────

    def _analisar_dual(self, image_base64: str, prompt: str, tipo_input: str) -> VisionResult:
        """Pipeline de imagem: Moondream local → Claude Vision fallback."""
        if self._disponivel is False:
            raise RuntimeError(
                "VisionService indisponível — nem Moondream local nem Claude API estão acessíveis"
            )

        b64 = image_base64
        if "," in b64 and b64.lstrip().startswith("data:"):
            b64 = b64.split(",", 1)[1]

        # 1) Moondream local (visão leve, cap 60s)
        if self._check_ollama():
            try:
                text = self._analisar_via_ollama(b64, prompt)
                result = self._parse_text_to_result(text, tipo_input)
                result.engine = "moondream_local"
                log.info("VisionService: engine=moondream_local OK")
                return result
            except Exception as e:
                log.warning(
                    "VisionService: Moondream falhou (%s) — fallback para Claude Vision", e,
                )

        # 2) Claude Vision fallback
        if self._claude_ok:
            text = self._analisar_via_claude(b64, prompt)
            result = self._parse_text_to_result(text, tipo_input)
            result.engine = "claude_api"
            log.info("VisionService: engine=claude_api OK")
            return result

        raise RuntimeError(
            "VisionService indisponível — nem Moondream local nem Claude API estão acessíveis"
        )

    # ── Dual engine orchestration — texto ────────────────────────────────────

    def _analisar_dual_texto(self, prompt: str) -> VisionResult:
        """Pipeline de texto: Gemma3 local → Claude Text fallback."""
        if self._disponivel is False:
            raise RuntimeError(
                "VisionService indisponível — nem Gemma3 local nem Claude API estão acessíveis"
            )

        # 1) Gemma3 local (texto puro, sem imagem)
        if self._check_ollama_text():
            try:
                text = self._analisar_via_ollama_texto(prompt)
                result = self._parse_text_to_result(text, "descricao")
                result.engine = "gemma3_local"
                log.info("VisionService: engine=gemma3_local OK")
                return result
            except Exception as e:
                log.warning(
                    "VisionService: Gemma3 texto falhou (%s) — fallback para Claude Text", e,
                )

        # 2) Claude Text fallback (sem imagem)
        if self._claude_ok:
            text = self._analisar_via_claude_texto(prompt)
            result = self._parse_text_to_result(text, "descricao")
            result.engine = "claude_api"
            log.info("VisionService: engine=claude_api (texto) OK")
            return result

        raise RuntimeError(
            "VisionService indisponível — nem Gemma3 local nem Claude API estão acessíveis"
        )

    # ── Ollama — visão ────────────────────────────────────────────────────────

    def _analisar_via_ollama(self, image_b64: str, prompt: str) -> str:
        """Chama Ollama /api/generate com imagem (Moondream). Timeout cap 60s."""
        payload = json.dumps({
            "model": self._ollama_vision_model,
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
        with urllib.request.urlopen(req, timeout=self._ollama_vision_timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        if "error" in data:
            raise RuntimeError(f"Ollama error: {data['error']}")
        text = data.get("response", "") or ""
        log.info("VisionService.ollama_vision: resposta raw_len=%d", len(text))
        if not text.strip():
            raise RuntimeError("Ollama retornou resposta vazia")
        return text

    # ── Ollama — texto ────────────────────────────────────────────────────────

    def _analisar_via_ollama_texto(self, prompt: str) -> str:
        """Chama Ollama /api/generate sem imagem (Gemma3 texto)."""
        payload = json.dumps({
            "model": self._ollama_text_model,
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self._ollama_url}/api/generate",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        # Text timeout capped at _OLLAMA_TEXT_TIMEOUT (30s) so total pipeline < nginx 60s
        _text_to = min(_OLLAMA_TEXT_TIMEOUT, self._ollama_timeout)
        with urllib.request.urlopen(req, timeout=_text_to) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        if "error" in data:
            raise RuntimeError(f"Ollama error: {data['error']}")
        text = data.get("response", "") or ""
        log.info("VisionService.ollama_texto: resposta raw_len=%d timeout=%ds", len(text), _text_to)
        if not text.strip():
            raise RuntimeError("Ollama retornou resposta vazia")
        return text

    # ── Claude — visão ────────────────────────────────────────────────────────

    def _analisar_via_claude(self, image_b64: str, prompt: str) -> str:
        """Chama Claude Vision API com imagem. Retorna texto cru."""
        if self._client is None:
            raise RuntimeError("Claude client não inicializado")
        media_type = self._detect_media_type(image_b64)
        msg = self._client.messages.create(
            model=_CLAUDE_MODEL,
            max_tokens=_MAX_TOKENS,
            timeout=25.0,  # 25s so vision pipeline (25+25) < nginx 60s
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
        log.info("VisionService.claude_vision: resposta raw_len=%d", len(raw_text))
        return raw_text

    # ── Claude — texto ────────────────────────────────────────────────────────

    def _analisar_via_claude_texto(self, prompt: str) -> str:
        """Chama Claude API com texto puro (sem imagem). Retorna texto cru."""
        if self._client is None:
            raise RuntimeError("Claude client não inicializado")
        msg = self._client.messages.create(
            model=_CLAUDE_MODEL,
            max_tokens=_MAX_TOKENS,
            timeout=20.0,  # 20s so text pipeline (30+20) < nginx 60s
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
        )
        raw_text = ""
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                raw_text += block.text
        log.info("VisionService.claude_texto: resposta raw_len=%d", len(raw_text))
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
    def _normalizar_dim(value: int, label: str) -> tuple[int, bool]:
        """Normalizes AI-returned dimensions to a valid mm range [100, 6000].

        Common AI errors:
          > 10000 → likely cm*100 (e.g. 90000 from "900cm * 100") → divide by 100
          < 100   → likely cm without conversion (e.g. 90cm) → multiply by 10
          After correction: clamp [100, 6000] with warning.

        Returns (corrected_value, was_normalized).
        """
        original = value
        normalized = False

        if value > 10000:
            value = round(value / 100)
            normalized = True
            log.info("VisionService._normalizar_dim: %s %d→%d (dividiu por 100, era cm*100)", label, original, value)
        elif value < 100:
            value = round(value * 10)
            normalized = True
            log.info("VisionService._normalizar_dim: %s %d→%d (multiplicou por 10, era cm)", label, original, value)

        if value > 6000:
            log.warning("VisionService._normalizar_dim: %s %d>6000 → clampando em 6000", label, value)
            value = 6000
            normalized = True
        elif value < 100:
            log.warning("VisionService._normalizar_dim: %s %d<100 → clampando em 100", label, value)
            value = 100
            normalized = True

        return value, normalized

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

        largura_raw = _i("largura_mm", 900)
        altura_raw  = _i("altura_mm", 2100)
        largura_norm, norm_l = VisionService._normalizar_dim(largura_raw, "largura_mm")
        altura_norm,  norm_a = VisionService._normalizar_dim(altura_raw,  "altura_mm")

        return VisionResult(
            tipologia_sugerida=_s("tipologia_sugerida", "porta_pivotante_simples"),
            largura_mm=largura_norm,
            altura_mm=altura_norm,
            tipo_abertura=_s("tipo_abertura", "pivotante"),
            num_folhas=_i("num_folhas", 1),
            espessura_vidro_mm=_i("espessura_vidro_mm", 8),
            cor_vidro=_s("cor_vidro", "incolor"),
            observacoes=_s("observacoes", ""),
            confianca=max(0.0, min(1.0, _f("confianca", 0.5))),
            raw=data,
            dimensoes_normalizadas=norm_l or norm_a,
        )
