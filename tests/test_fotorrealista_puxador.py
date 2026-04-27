"""
Testes para o parâmetro puxador_codigo no endpoint /fotorrealista.

cairosvg é mockado no nível do módulo (import movido para topo em viewer_3d.py).
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


@pytest.fixture
def client_with_mock_cairosvg():
    cairosvg_mock = MagicMock()
    cairosvg_mock.svg2png.return_value = _FAKE_PNG
    with patch.dict(sys.modules, {"cairosvg": cairosvg_mock}):
        import importlib
        import app.routers.viewer_3d as v3d
        v3d.cairosvg = cairosvg_mock
        from app.main import app
        yield TestClient(app), cairosvg_mock


def test_fotorrealista_aceita_puxador_codigo_param(client_with_mock_cairosvg):
    client, _ = client_with_mock_cairosvg
    res = client.get(
        "/api/v1/tipologia/porta_pivotante_simples/fotorrealista"
        "?largura=900&altura=2100&puxador_codigo=AL1629A"
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"


def test_fotorrealista_sem_puxador_codigo_mantem_padrao(client_with_mock_cairosvg):
    client, _ = client_with_mock_cairosvg
    res = client.get(
        "/api/v1/tipologia/porta_pivotante_simples/fotorrealista"
        "?largura=900&altura=2100"
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"


def test_fotorrealista_puxador_codigo_invalido_retorna_400(client_with_mock_cairosvg):
    client, _ = client_with_mock_cairosvg
    res = client.get(
        "/api/v1/tipologia/porta_pivotante_simples/fotorrealista"
        "?largura=900&altura=2100&puxador_codigo="
    )
    assert res.status_code == 400
