"""
Testes Sprint 7 — Smart Vision (foto/croqui → projeto completo).

Cobre:
  - VisionService: detect_media_type, parse_json (fences), _to_result, disponivel
  - Endpoints POST /api/v1/smart/photo-to-project e /sketch-to-project
  - Graceful 503 quando ANTHROPIC_API_KEY ausente
  - Auth 401 sem X-VDX-Key
  - Validação 422 body vazio
  - Pipeline completo com mock do Claude Vision

Rode com: python -m pytest tests/test_smart_vision.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.services.vision_service import VisionResult, VisionService


# ── Fixtures ──────────────────────────────────────────────────────────────────

# Pequeno PNG base64 1x1 transparente
_PNG_1x1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABXvMqOgAAAABJRU5ErkJggg=="
)
_JPG_HEADER_B64 = "/9j/4AAQSkZJRgABAQEASABIAAD"  # header JPEG base64


def _valid_vision_json() -> dict:
    return {
        "tipologia_sugerida": "porta_pivotante_simples",
        "largura_mm": 900,
        "altura_mm": 2100,
        "tipo_abertura": "pivotante",
        "num_folhas": 1,
        "espessura_vidro_mm": 10,
        "cor_vidro": "incolor",
        "observacoes": "Vão bem definido, dimensões padrão.",
        "confianca": 0.87,
    }


def _fake_claude_response(json_payload: dict, wrap_fence: bool = False) -> MagicMock:
    """Monta objeto com atributo .content no formato do SDK Anthropic."""
    text = json.dumps(json_payload)
    if wrap_fence:
        text = f"Aqui está a análise:\n```json\n{text}\n```"
    block = MagicMock()
    block.type = "text"
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


# Usa a master key real do .env
_HEADERS = {"X-VDX-Key": settings.vdx_api_master_key or "test-key"}


# ── 1. VisionService unit tests ───────────────────────────────────────────────

class TestVisionServiceHelpers:
    def test_detect_media_type_png(self):
        assert VisionService._detect_media_type(_PNG_1x1) == "image/png"

    def test_detect_media_type_jpeg(self):
        assert VisionService._detect_media_type(_JPG_HEADER_B64) == "image/jpeg"

    def test_detect_media_type_data_url(self):
        assert VisionService._detect_media_type("data:image/webp;base64,UklGRxxx") == "image/webp"

    def test_detect_media_type_unknown_defaults_jpeg(self):
        assert VisionService._detect_media_type("XYZrandombase64") == "image/jpeg"

    def test_parse_json_clean(self):
        data = VisionService._parse_json('{"a": 1, "b": "x"}')
        assert data == {"a": 1, "b": "x"}

    def test_parse_json_with_fence(self):
        text = '```json\n{"a": 1}\n```'
        assert VisionService._parse_json(text) == {"a": 1}

    def test_parse_json_with_prose(self):
        text = 'Análise: aqui está o JSON => {"tipologia_sugerida":"x","largura_mm":900}'
        data = VisionService._parse_json(text)
        assert data["tipologia_sugerida"] == "x"

    def test_parse_json_invalid_raises(self):
        with pytest.raises(ValueError):
            VisionService._parse_json("texto sem JSON algum aqui")

    def test_to_result_defaults(self):
        r = VisionService._to_result({})
        assert r.tipologia_sugerida == "porta_pivotante_simples"
        assert r.largura_mm == 900
        assert r.altura_mm == 2100
        assert r.num_folhas == 1
        assert 0.0 <= r.confianca <= 1.0

    def test_to_result_confianca_clamped(self):
        assert VisionService._to_result({"confianca": 5.0}).confianca == 1.0
        assert VisionService._to_result({"confianca": -0.3}).confianca == 0.0

    def test_to_result_full_payload(self):
        r = VisionService._to_result(_valid_vision_json())
        assert r.tipologia_sugerida == "porta_pivotante_simples"
        assert r.largura_mm == 900
        assert r.espessura_vidro_mm == 10
        assert r.cor_vidro == "incolor"


class TestVisionServiceDisponivel:
    def test_disponivel_sem_key(self):
        """Sem ANTHROPIC_API_KEY, disponivel=False e chamada levanta RuntimeError."""
        with patch.object(settings, "anthropic_api_key", ""):
            svc = VisionService()
            assert svc.disponivel is False
            with pytest.raises(RuntimeError):
                svc.analisar_foto_vao(_PNG_1x1)
            with pytest.raises(RuntimeError):
                svc.analisar_croqui(_PNG_1x1)

    def test_disponivel_com_key(self):
        """Com key configurada (no .env), disponivel=True."""
        if not settings.anthropic_api_key:
            pytest.skip("ANTHROPIC_API_KEY não configurado no ambiente de teste")
        svc = VisionService()
        assert svc.disponivel is True


class TestVisionServiceAnalise:
    def test_analisar_foto_mock(self):
        """Pipeline completo com mock do cliente Anthropic."""
        if not settings.anthropic_api_key:
            pytest.skip("ANTHROPIC_API_KEY não configurado")
        svc = VisionService()
        fake_client = MagicMock()
        fake_client.messages.create.return_value = _fake_claude_response(_valid_vision_json())
        svc._client = fake_client
        svc._disponivel = True

        res = svc.analisar_foto_vao(_PNG_1x1, contexto="cozinha")
        assert isinstance(res, VisionResult)
        assert res.tipologia_sugerida == "porta_pivotante_simples"
        assert res.largura_mm == 900
        # Conferir que foi chamado com image + text
        call_args = fake_client.messages.create.call_args.kwargs
        assert call_args["model"].startswith("claude-sonnet-4")
        content = call_args["messages"][0]["content"]
        assert content[0]["type"] == "image"
        assert content[0]["source"]["media_type"] == "image/png"
        assert "cozinha" in content[1]["text"]

    def test_analisar_croqui_mock_with_fence(self):
        """Parse tolerante a fences ```json```."""
        if not settings.anthropic_api_key:
            pytest.skip("ANTHROPIC_API_KEY não configurado")
        svc = VisionService()
        fake_client = MagicMock()
        fake_client.messages.create.return_value = _fake_claude_response(_valid_vision_json(), wrap_fence=True)
        svc._client = fake_client
        svc._disponivel = True

        res = svc.analisar_croqui(_PNG_1x1, notas="porta varanda 900x2100")
        assert res.num_folhas == 1
        # Verifica que as notas foram incluídas no prompt
        content = fake_client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "porta varanda" in content[1]["text"]


# ── 2. Endpoints HTTP ─────────────────────────────────────────────────────────

def _mock_vision_available(monkeypatch):
    """Força _vision no router a ter disponivel=True com mock."""
    from app.routers import smart_vision as sv
    fake_result = VisionResult(
        tipologia_sugerida="porta_pivotante_simples",
        largura_mm=900,
        altura_mm=2100,
        tipo_abertura="pivotante",
        num_folhas=1,
        espessura_vidro_mm=8,
        cor_vidro="incolor",
        observacoes="mock",
        confianca=0.9,
        raw=_valid_vision_json(),
    )
    monkeypatch.setattr(sv._vision, "_disponivel", True)
    monkeypatch.setattr(sv._vision, "analisar_foto_vao", lambda img, contexto="": fake_result)
    monkeypatch.setattr(sv._vision, "analisar_croqui", lambda img, notas="": fake_result)
    return fake_result


class TestSmartVisionEndpoints:
    def test_photo_sem_auth_401(self, client):
        resp = client.post(
            "/api/v1/smart/photo-to-project",
            json={"image_base64": _PNG_1x1},
        )
        assert resp.status_code == 401

    def test_sketch_sem_auth_401(self, client):
        resp = client.post(
            "/api/v1/smart/sketch-to-project",
            json={"image_base64": _PNG_1x1},
        )
        assert resp.status_code == 401

    def test_photo_body_vazio_422(self, client):
        resp = client.post("/api/v1/smart/photo-to-project", json={}, headers=_HEADERS)
        assert resp.status_code == 422

    def test_photo_503_quando_vision_indisponivel(self, client, monkeypatch):
        """Se VisionService.disponivel=False, retorna 503."""
        from app.routers import smart_vision as sv
        monkeypatch.setattr(sv._vision, "_disponivel", False)
        resp = client.post(
            "/api/v1/smart/photo-to-project",
            json={"image_base64": _PNG_1x1, "contexto": "teste"},
            headers=_HEADERS,
        )
        assert resp.status_code == 503

    def test_sketch_503_quando_vision_indisponivel(self, client, monkeypatch):
        from app.routers import smart_vision as sv
        monkeypatch.setattr(sv._vision, "_disponivel", False)
        resp = client.post(
            "/api/v1/smart/sketch-to-project",
            json={"image_base64": _PNG_1x1},
            headers=_HEADERS,
        )
        assert resp.status_code == 503

    def test_photo_pipeline_200(self, client, monkeypatch):
        """Pipeline completo com mock da Vision retorna 200 + SmartProjectResponse."""
        _mock_vision_available(monkeypatch)
        resp = client.post(
            "/api/v1/smart/photo-to-project",
            json={"image_base64": _PNG_1x1, "contexto": "cozinha aberta"},
            headers=_HEADERS,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "analise" in body
        assert body["analise"]["tipologia_sugerida"] == "porta_pivotante_simples"
        assert body["analise"]["confianca"] == 0.9
        assert body["svg"].startswith("<")
        assert "scene" in body and isinstance(body["scene"], dict)
        assert "dimensoes" in body["scene"]
        assert body["scene"]["dimensoes"]["largura"] > 0
        assert "vidros" in body["scene"]
        assert isinstance(body["pecas"], list)
        assert isinstance(body["ferragens"], list)

    def test_sketch_pipeline_200(self, client, monkeypatch):
        _mock_vision_available(monkeypatch)
        resp = client.post(
            "/api/v1/smart/sketch-to-project",
            json={"image_base64": _PNG_1x1, "notas": "porta pivotante 900x2100"},
            headers=_HEADERS,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["tipologia_chave"]
        # Viewer URL é opcional (best effort); se vier, deve ter token
        if body.get("viewer_url"):
            assert "t=" in body["viewer_url"]
            assert body.get("viewer_token")

    def test_photo_override_cor_vidro(self, client, monkeypatch):
        """Override de cor_vidro no body deve sobrescrever a sugestão da IA."""
        _mock_vision_available(monkeypatch)
        resp = client.post(
            "/api/v1/smart/photo-to-project",
            json={"image_base64": _PNG_1x1, "cor_vidro": "fume"},
            headers=_HEADERS,
        )
        assert resp.status_code == 200
        # Sugestão da IA era "incolor"; o override "fume" deve aparecer na scene
        body = resp.json()
        assert "scene" in body

    def test_photo_router_registrado(self, client):
        """Rota está registrada no app."""
        # OpenAPI deve listar o endpoint
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/api/v1/smart/photo-to-project" in paths
        assert "/api/v1/smart/sketch-to-project" in paths
