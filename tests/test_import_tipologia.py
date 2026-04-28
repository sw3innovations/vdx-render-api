"""
Testes para POST /api/v1/import/tipologia.

Ferragens reais do catálogo:
  - puxador válido: codigo_normalizado='1629', fabricante_id='HE'
  - dobradica válida: codigo_normalizado='1101', fabricante_id='SM'
"""
import os
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

_BODY_SEM_PNG = {
    "nome": "Porta Customizada",
    "paineis": [
        {
            "nome": "Porta",
            "largura_mm": 900,
            "altura_mm": 2100,
            "classificacao": "movel",
            "ferragens": [],
        }
    ],
    "opcoes": {"cor": "incolor", "acabamento": "cromado", "incluir_png": False},
}


@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture
def client_com_png_mock():
    """Fixture com cairosvg mockado para o módulo import_tipologia."""
    cairosvg_mock = MagicMock()
    cairosvg_mock.svg2png.return_value = _FAKE_PNG
    from app.main import app
    import app.routers.import_tipologia as imp
    original = imp.cairosvg
    imp.cairosvg = cairosvg_mock
    yield TestClient(app), cairosvg_mock
    imp.cairosvg = original


# ─── Testes de sucesso ────────────────────────────────────────────────────────

def test_import_tipologia_simples_retorna_200(client):
    res = client.post("/api/v1/import/tipologia", json=_BODY_SEM_PNG)
    assert res.status_code == 200


def test_import_svg_contém_tag_svg(client):
    res = client.post("/api/v1/import/tipologia", json=_BODY_SEM_PNG)
    assert res.status_code == 200
    assert "<svg" in res.json()["svg"]


def test_import_png_criado_em_disco(client_com_png_mock):
    client, _ = client_com_png_mock
    body = {**_BODY_SEM_PNG, "opcoes": {"incluir_png": True}}
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 200
    data = res.json()
    assert data["png_url"] is not None
    uid = data["png_url"].split("/")[-2]
    assert (Path("uploads/import") / uid / "render.png").exists()


def test_import_sem_ferragens_retorna_200(client):
    body = {
        "nome": "Fachada Fixa",
        "paineis": [{"nome": "Fixo", "largura_mm": 1200, "altura_mm": 2400, "ferragens": []}],
        "opcoes": {"incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 200


def test_import_varios_paineis_retorna_200(client):
    body = {
        "nome": "Box 2 Folhas",
        "paineis": [
            {"nome": "Fixo", "largura_mm": 400, "altura_mm": 1900},
            {"nome": "Movel", "largura_mm": 600, "altura_mm": 1900},
            {"nome": "Fixo 2", "largura_mm": 400, "altura_mm": 1900},
        ],
        "opcoes": {"incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 200


def test_import_resposta_tem_campo_avisos(client):
    res = client.post("/api/v1/import/tipologia", json=_BODY_SEM_PNG)
    assert res.status_code == 200
    assert "avisos" in res.json()


def test_import_resposta_tem_tipologia_chave(client):
    res = client.post("/api/v1/import/tipologia", json=_BODY_SEM_PNG)
    assert res.status_code == 200
    data = res.json()
    assert "tipologia_chave" in data
    assert len(data["tipologia_chave"]) == 36  # UUID format


def test_import_fabricante_especifico_valido_retorna_200(client):
    body = {
        "nome": "Porta com Puxador HE",
        "paineis": [
            {
                "nome": "Porta",
                "largura_mm": 900,
                "altura_mm": 2100,
                "ferragens": [
                    {
                        "codigo": "1629",
                        "fabricante_id": "HE",
                        "tipo": "puxador",
                        "x_mm": 450,
                        "y_mm": 1050,
                    }
                ],
            }
        ],
        "opcoes": {"incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 200


# ─── Testes de erro — 400 (regra de negócio) ─────────────────────────────────

def test_import_ferragem_invalida_retorna_400(client):
    body = {
        "nome": "Porta",
        "paineis": [
            {
                "nome": "Porta",
                "largura_mm": 900,
                "altura_mm": 2100,
                "ferragens": [
                    {
                        "codigo": "CODIGO_INEXISTENTE_99999",
                        "tipo": "puxador",
                        "x_mm": 450,
                        "y_mm": 1050,
                    }
                ],
            }
        ],
        "opcoes": {"incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 400


def test_import_fabricante_invalido_retorna_400(client):
    body = {
        "nome": "Porta",
        "paineis": [
            {
                "nome": "Porta",
                "largura_mm": 900,
                "altura_mm": 2100,
                "ferragens": [
                    {
                        "codigo": "1629",
                        "fabricante_id": "XX",
                        "tipo": "puxador",
                        "x_mm": 450,
                        "y_mm": 1050,
                    }
                ],
            }
        ],
        "opcoes": {"incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 400


# ─── Testes de erro — 422 (validação Pydantic) ───────────────────────────────

def test_import_largura_painel_fora_limite_retorna_422(client):
    body = {
        "nome": "Inválida",
        "paineis": [{"nome": "X", "largura_mm": 50, "altura_mm": 2100}],
        "opcoes": {"incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 422


def test_import_cor_invalida_retorna_422(client):
    body = {
        "nome": "Teste",
        "paineis": [{"nome": "X", "largura_mm": 900, "altura_mm": 2100}],
        "opcoes": {"cor": "roxo", "incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 422


def test_import_acabamento_invalido_retorna_422(client):
    body = {
        "nome": "Teste",
        "paineis": [{"nome": "X", "largura_mm": 900, "altura_mm": 2100}],
        "opcoes": {"acabamento": "prata", "incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 422


def test_import_paineis_vazios_retorna_422(client):
    body = {
        "nome": "Sem paineis",
        "paineis": [],
        "opcoes": {"incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 422
