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


# ─── Entrega 6.5 — campos adicionais (todos opcionais) ───────────────────────

def test_import_aceita_categoria_opcional(client):
    body = {**_BODY_SEM_PNG, "categoria": "box"}
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 200
    assert "tipologia_chave" in res.json()


def test_import_aceita_posicao_x_y_em_painel(client):
    body = {
        "nome": "Painel Posicionado",
        "paineis": [{"nome": "Porta", "largura_mm": 900, "altura_mm": 2100,
                     "posicao_x_mm": 0, "posicao_y_mm": 0}],
        "opcoes": {"incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 200
    assert "<svg" in res.json()["svg"]


def test_import_box_canto_90_com_paineis_em_L_retorna_200(client):
    body = {
        "nome": "Box Canto 90",
        "categoria": "box",
        "paineis": [
            {"nome": "Lateral", "largura_mm": 900, "altura_mm": 2000,
             "classificacao": "fixo", "posicao_x_mm": 0, "posicao_y_mm": 0},
            {"nome": "Frontal", "largura_mm": 900, "altura_mm": 2000,
             "classificacao": "movel", "posicao_x_mm": 900, "posicao_y_mm": 0,
             "abertura": {"modo": "abrir", "lado_dobradica": "esquerda"}},
        ],
        "opcoes": {"cor": "fume", "acabamento": "cromado", "incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 200
    assert "<svg" in res.json()["svg"]


def test_import_painel_com_abertura_abrir_renderiza_seta(client):
    body = {
        "nome": "Porta Abrir",
        "paineis": [{"nome": "Porta", "largura_mm": 900, "altura_mm": 2100,
                     "abertura": {"modo": "abrir", "lado_dobradica": "esquerda"}}],
        "opcoes": {"incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 200
    # stroke-dasharray="5 3" identifica o indicador de abertura
    assert "5 3" in res.json()["svg"]


def test_import_aceita_incluir_pdf_e_retorna_url(client):
    body = {**_BODY_SEM_PNG, "opcoes": {"incluir_pdf": True, "incluir_png": False}}
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 200
    assert res.json()["pdf_url"] is not None


def test_import_aceita_incluir_3d_e_retorna_viewer_url(client):
    body = {**_BODY_SEM_PNG, "opcoes": {"incluir_3d": True, "incluir_png": False}}
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 200
    assert res.json()["viewer_3d_url"] is not None


def test_import_resposta_inclui_ferragens_resolvidas(client):
    body = {
        "nome": "Porta com Ferragem",
        "paineis": [
            {
                "nome": "Porta",
                "largura_mm": 900,
                "altura_mm": 2100,
                "ferragens": [{"codigo": "1629", "fabricante_id": "HE",
                               "tipo": "puxador", "x_mm": 450, "y_mm": 1050}],
            }
        ],
        "opcoes": {"incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 200
    data = res.json()
    assert "ferragens_resolvidas" in data
    assert isinstance(data["ferragens_resolvidas"], list)
    assert len(data["ferragens_resolvidas"]) == 1
    assert data["ferragens_resolvidas"][0]["codigo"] == "1629"


def test_import_sem_posicao_mantem_comportamento_atual_lado_a_lado(client):
    body = {
        "nome": "Dois Paineis Lado a Lado",
        "paineis": [
            {"nome": "Fixo", "largura_mm": 500, "altura_mm": 1800},
            {"nome": "Movel", "largura_mm": 700, "altura_mm": 1800},
        ],
        "opcoes": {"incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 200
    assert "<svg" in res.json()["svg"]


def test_import_abertura_abrir_sem_lado_dobradica_warning_nao_erro(client):
    body = {
        "nome": "Porta sem Lado Dobradica",
        "paineis": [{"nome": "Porta", "largura_mm": 900, "altura_mm": 2100,
                     "abertura": {"modo": "abrir"}}],
        "opcoes": {"incluir_png": False},
    }
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 200
    avisos = res.json()["avisos"]
    assert any("dobradiça" in av or "lado" in av.lower() for av in avisos)


def test_import_categoria_invalida_retorna_422(client):
    body = {**_BODY_SEM_PNG, "categoria": "invalida"}
    res = client.post("/api/v1/import/tipologia", json=body)
    assert res.status_code == 422
