"""Testes do sistema de view token (JWT HS256) do VDX Glass Engine.

Cobre:
- encode/decode básico
- TTL e expiração
- Assinatura inválida (forja de payload)
- Tipo errado
- Claims corretas preservadas
- Endpoint POST /api/v1/3d/viewer/token
- Endpoint GET /api/v1/3d/viewer — modo token e modo header
"""
import time

import pytest
from fastapi.testclient import TestClient

from app.core import view_token as vt
from app.main import app

_SECRET = "test-secret-abcdef1234567890"
_HEADERS = {"X-VDX-Key": "test-key"}


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def claims():
    return vt.new_claims(
        tip="porta_pivotante_simples",
        w=900.0,
        h=2100.0,
        cv="incolor",
        fab=None,
        esp=8.0,
        ttl_seconds=3600,
    )


# ─── Unit: encode/decode ──────────────────────────────────────────────────────

def test_encode_retorna_tres_partes(claims):
    token = vt.encode(claims, _SECRET)
    assert token.count(".") == 2


def test_decode_round_trip(claims):
    token = vt.encode(claims, _SECRET)
    decoded = vt.decode(token, _SECRET)
    assert decoded.tip == "porta_pivotante_simples"
    assert decoded.w == 900.0
    assert decoded.h == 2100.0
    assert decoded.cv == "incolor"
    assert decoded.fab is None
    assert decoded.esp == 8.0


def test_decode_fabricante_preservado():
    claims = vt.new_claims("box_banheiro", 1200, 2000, "fume", "HE", 6.0, 3600)
    token = vt.encode(claims, _SECRET)
    decoded = vt.decode(token, _SECRET)
    assert decoded.fab == "HE"
    assert decoded.cv == "fume"


# ─── Unit: TTL / expiração ────────────────────────────────────────────────────

def test_token_expirado_levanta_expired():
    claims = vt.new_claims("janela", 600, 1200, "default", None, 8.0, ttl_seconds=-1)
    token = vt.encode(claims, _SECRET)
    with pytest.raises(vt.ViewTokenExpiredError):
        vt.decode(token, _SECRET)


def test_token_valido_nao_expira_antes_do_tempo(claims):
    token = vt.encode(claims, _SECRET)
    decoded = vt.decode(token, _SECRET)
    assert decoded.exp > int(time.time())


# ─── Unit: assinatura / integridade ──────────────────────────────────────────

def test_assinatura_incorreta_levanta_invalid(claims):
    token = vt.encode(claims, _SECRET)
    with pytest.raises(vt.ViewTokenInvalidError):
        vt.decode(token, "wrong-secret")


def test_payload_adulterado_levanta_invalid(claims):
    import base64, json

    token = vt.encode(claims, _SECRET)
    header, payload_b64, sig = token.split(".")

    # Decodifica, altera dimensão, recodifica SEM nova assinatura
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    payload["w"] = 99999.0  # valor fora do range — forja

    new_payload = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()

    tampered = f"{header}.{new_payload}.{sig}"
    with pytest.raises(vt.ViewTokenInvalidError):
        vt.decode(tampered, _SECRET)


def test_formato_invalido_levanta_invalid():
    with pytest.raises(vt.ViewTokenInvalidError):
        vt.decode("nao.e.um.jwt.valido.com.cinco.partes", _SECRET)

    with pytest.raises(vt.ViewTokenInvalidError):
        vt.decode("apenas_uma_parte", _SECRET)


def test_tipo_errado_levanta_invalid(claims):
    import base64, json

    token = vt.encode(claims, _SECRET)
    header, payload_b64, _ = token.split(".")

    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    payload["typ"] = "access"  # tipo errado

    # Assina com o segredo correto — mas tipo é "access"
    new_payload = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()

    import hashlib, hmac as _hmac
    msg = f"{header}.{new_payload}".encode()
    sig = base64.urlsafe_b64encode(
        _hmac.new(_SECRET.encode(), msg, hashlib.sha256).digest()
    ).rstrip(b"=").decode()

    with pytest.raises(vt.ViewTokenInvalidError, match="Tipo"):
        vt.decode(f"{header}.{new_payload}.{sig}", _SECRET)


# ─── Endpoint: POST /api/v1/3d/viewer/token ──────────────────────────────────

def test_token_endpoint_retorna_200(client):
    res = client.post(
        "/api/v1/3d/viewer/token",
        json={
            "tipologia": "porta_pivotante_simples",
            "largura": 900,
            "altura": 2100,
        },
        headers=_HEADERS,
    )
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert "url" in data
    assert "expires_in" in data
    assert data["token"].count(".") == 2
    assert "/api/v1/3d/viewer?t=" in data["url"]


def test_token_endpoint_sem_auth_retorna_401(client):
    res = client.post(
        "/api/v1/3d/viewer/token",
        json={"tipologia": "porta_pivotante_simples", "largura": 900, "altura": 2100},
    )
    assert res.status_code == 401


def test_token_endpoint_dimensao_invalida(client):
    res = client.post(
        "/api/v1/3d/viewer/token",
        json={"tipologia": "porta_pivotante_simples", "largura": 50, "altura": 2100},
        headers=_HEADERS,
    )
    assert res.status_code == 422


def test_token_endpoint_ttl_customizado(client):
    res = client.post(
        "/api/v1/3d/viewer/token",
        json={
            "tipologia": "janela_3_folhas",
            "largura": 1500,
            "altura": 1200,
            "ttl_seconds": 600,
        },
        headers=_HEADERS,
    )
    assert res.status_code == 200
    assert res.json()["expires_in"] == 600


# ─── Endpoint: GET /api/v1/3d/viewer ─────────────────────────────────────────

def test_viewer_modo_header_retorna_html(client):
    res = client.get(
        "/api/v1/3d/viewer",
        params={"tipologia": "porta_pivotante_simples", "largura": 900, "altura": 2100},
        headers=_HEADERS,
    )
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "babylon" in res.text.lower()


def test_viewer_modo_token_retorna_html(client):
    # Primeiro emite um token
    token_res = client.post(
        "/api/v1/3d/viewer/token",
        json={"tipologia": "porta_pivotante_simples", "largura": 900, "altura": 2100},
        headers=_HEADERS,
    )
    token = token_res.json()["token"]

    # Agora acessa o viewer com o token (sem header)
    res = client.get("/api/v1/3d/viewer", params={"t": token})
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "babylon" in res.text.lower()


def test_viewer_sem_auth_retorna_html_401(client):
    res = client.get(
        "/api/v1/3d/viewer",
        params={"tipologia": "porta_pivotante_simples", "largura": 900, "altura": 2100},
    )
    assert res.status_code == 401
    assert "text/html" in res.headers["content-type"]
    assert "Autenticação necessária" in res.text


def test_viewer_token_expirado_retorna_html_401(client):
    from app.config import settings as _settings

    claims = vt.new_claims("porta_pivotante_simples", 900, 2100, "default", None, 8.0, ttl_seconds=-1)
    expired_token = vt.encode(claims, _settings.view_token_secret)

    res = client.get("/api/v1/3d/viewer", params={"t": expired_token})
    assert res.status_code == 401
    assert "text/html" in res.headers["content-type"]
    assert "expirado" in res.text.lower()


def test_viewer_token_invalido_retorna_html_401(client):
    res = client.get("/api/v1/3d/viewer", params={"t": "nao.e.valido"})
    assert res.status_code == 401
    assert "inválido" in res.text.lower()


# ─── E2E: fluxo completo ──────────────────────────────────────────────────────

def test_e2e_token_viewer_completo(client):
    """Emite token → acessa viewer → valida scene embutida."""
    # 1. Emitir token
    token_res = client.post(
        "/api/v1/3d/viewer/token",
        json={
            "tipologia": "janela_3_folhas",
            "largura": 1500,
            "altura": 1200,
            "cor_vidro": "verde",
            "espessura": 6.0,
        },
        headers=_HEADERS,
    )
    assert token_res.status_code == 200
    token = token_res.json()["token"]

    # 2. Acessar viewer com token (sem header — simula browser)
    viewer_res = client.get("/api/v1/3d/viewer", params={"t": token})
    assert viewer_res.status_code == 200

    html = viewer_res.text
    # Scene JSON deve estar embutida
    assert "const SCENE" in html
    # Não deve ter query params de dimensão expostos na URL do viewer
    assert "largura" not in html.split("const SCENE")[0]
