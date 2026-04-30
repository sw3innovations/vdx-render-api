"""Testes para POST /api/v1/editor/salvar e GET /api/v1/editor/{uuid}."""
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

_TIPOLOGIA_BODY = {
    "nome": "Porta Editor Test",
    "categoria": "porta",
    "paineis": [
        {
            "nome": "Painel",
            "largura_mm": 900,
            "altura_mm": 2100,
            "classificacao": "movel",
            "ferragens": [],
            "posicao_x_mm": 50,
            "posicao_y_mm": 0,
        }
    ],
    "opcoes": {
        "cor": "incolor",
        "acabamento": "cromado",
        "incluir_png": False,
        "incluir_pdf": False,
        "incluir_3d": False,
    },
}


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_post_editor_salvar_retorna_chave(client: TestClient):
    """POST /salvar deve retornar editor_chave e url válidos."""
    resp = client.post("/api/v1/editor/salvar", json=_TIPOLOGIA_BODY)
    assert resp.status_code == 200
    data = resp.json()
    assert "editor_chave" in data
    assert "url" in data
    assert data["url"].startswith("/editor?carregar=")
    assert data["editor_chave"] in data["url"]


def test_post_editor_salvar_persiste_tipologia(client: TestClient):
    """POST /salvar deve incluir tipologia_json no retorno."""
    resp = client.post("/api/v1/editor/salvar", json=_TIPOLOGIA_BODY)
    assert resp.status_code == 200
    data = resp.json()
    assert "tipologia_json" in data
    tj = data["tipologia_json"]
    assert tj["nome"] == _TIPOLOGIA_BODY["nome"]
    assert len(tj["paineis"]) == 1
    assert tj["paineis"][0]["largura_mm"] == 900


def test_get_editor_recupera_estado_salvo(client: TestClient):
    """GET /api/v1/editor/{uuid} deve devolver o estado salvo."""
    save_resp = client.post("/api/v1/editor/salvar", json=_TIPOLOGIA_BODY)
    assert save_resp.status_code == 200
    chave = save_resp.json()["editor_chave"]

    get_resp = client.get(f"/api/v1/editor/{chave}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["editor_chave"] == chave
    assert data["tipologia_json"]["nome"] == _TIPOLOGIA_BODY["nome"]
    assert data["tipologia_json"]["paineis"][0]["posicao_x_mm"] == 50
