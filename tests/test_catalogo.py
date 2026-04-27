"""
Testes para app/routers/catalogo.py — endpoints públicos de ferragens e kits.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import os

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


# ─── Ferragens ────────────────────────────────────────────────────────────────

def test_listar_todas_ferragens_retorna_lista(client):
    res = client.get("/api/v1/catalogo/ferragens")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_listar_todas_ferragens_quantidade(client):
    res = client.get("/api/v1/catalogo/ferragens")
    assert res.status_code == 200
    # DB tem 158 ferragens
    assert len(res.json()) == 158


def test_estrutura_ferragem_tem_campos_esperados(client):
    res = client.get("/api/v1/catalogo/ferragens")
    assert res.status_code == 200
    item = res.json()[0]
    for campo in ("codigo", "nome", "tipo", "fabricante_id"):
        assert campo in item, f"Campo '{campo}' ausente na resposta"


def test_listar_ferragens_filtro_tipo_puxador(client):
    res = client.get("/api/v1/catalogo/ferragens?tipo=puxador")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 10
    for item in data:
        assert item["tipo"] == "puxador"


def test_listar_ferragens_filtro_tipo_invalido_retorna_lista_vazia(client):
    res = client.get("/api/v1/catalogo/ferragens?tipo=tipo_inexistente_xyz")
    assert res.status_code == 200
    assert res.json() == []


def test_listar_ferragens_filtro_fabricante(client):
    res = client.get("/api/v1/catalogo/ferragens?fabricante=SM")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    for item in data:
        assert item["fabricante_id"] == "SM"


def test_listar_ferragens_por_tipo_path(client):
    res = client.get("/api/v1/catalogo/ferragens/puxador")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 10
    for item in data:
        assert item["tipo"] == "puxador"


def test_listar_ferragens_por_tipo_invalido_retorna_404(client):
    res = client.get("/api/v1/catalogo/ferragens/tipo_inexistente_xyz")
    assert res.status_code == 404


# ─── Kits ─────────────────────────────────────────────────────────────────────

def test_listar_kits_retorna_lista(client):
    res = client.get("/api/v1/catalogo/kits")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_listar_kits_quantidade(client):
    res = client.get("/api/v1/catalogo/kits")
    assert res.status_code == 200
    # DB tem 48 kits
    assert len(res.json()) == 48


def test_estrutura_kit_tem_campos_esperados(client):
    res = client.get("/api/v1/catalogo/kits")
    assert res.status_code == 200
    kit = res.json()[0]
    for campo in ("id", "numero", "nome", "fabricante_id", "componentes"):
        assert campo in kit, f"Campo '{campo}' ausente no kit"


def test_kit_tem_componentes(client):
    res = client.get("/api/v1/catalogo/kits")
    assert res.status_code == 200
    kits_com_componentes = [k for k in res.json() if len(k["componentes"]) > 0]
    assert len(kits_com_componentes) > 0


def test_listar_kits_por_tipologia_porta_pivotante(client):
    res = client.get("/api/v1/catalogo/kits/porta_pivotante_simples")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    # Nome do kit deve conter "pivotante" (case-insensitive)
    nomes = [k["nome"].lower() for k in data]
    assert any("pivotante" in n for n in nomes)


def test_listar_kits_filtro_tipologia_query_param(client):
    res = client.get("/api/v1/catalogo/kits?tipologia=porta_pivotante_simples")
    assert res.status_code == 200
    assert len(res.json()) > 0


def test_listar_kits_tipologia_inexistente_retorna_404(client):
    res = client.get("/api/v1/catalogo/kits/tipologia_completamente_inexistente_xyz")
    assert res.status_code == 404
