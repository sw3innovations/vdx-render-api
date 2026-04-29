"""Testes dos endpoints /api/v1/canonical/* — Sprint 10."""
import os
import pytest

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _run_etl():
    """Garante que o schema canônico está populado antes dos testes."""
    from app.etl.loaders.load_canonical import CanonicalLoader
    with CanonicalLoader() as loader:
        loader.reset()
        loader.run()


# ── /api/v1/canonical/materiais ───────────────────────────────────────────────

def test_listar_materiais_200():
    r = client.get("/api/v1/canonical/materiais")
    assert r.status_code == 200


def test_listar_materiais_tem_campos():
    body = client.get("/api/v1/canonical/materiais").json()
    assert "total" in body
    assert "materiais" in body
    assert body["total"] >= 9


# ── /api/v1/canonical/acabamentos ────────────────────────────────────────────

def test_listar_acabamentos_200():
    r = client.get("/api/v1/canonical/acabamentos")
    assert r.status_code == 200


def test_listar_acabamentos_tem_campos():
    body = client.get("/api/v1/canonical/acabamentos").json()
    assert "total" in body
    assert body["total"] >= 11


# ── /api/v1/canonical/variaveis ───────────────────────────────────────────────

def test_listar_variaveis_200():
    r = client.get("/api/v1/canonical/variaveis")
    assert r.status_code == 200


def test_listar_variaveis_filtro_eixo_altura():
    body = client.get("/api/v1/canonical/variaveis?eixo=altura").json()
    for v in body["variaveis"]:
        assert v["eixo"] == "altura"


def test_listar_variaveis_filtro_eixo_largura():
    body = client.get("/api/v1/canonical/variaveis?eixo=largura").json()
    for v in body["variaveis"]:
        assert v["eixo"] == "largura"


# ── /api/v1/canonical/tipologias ──────────────────────────────────────────────

def test_listar_tipologias_canonicas_200():
    r = client.get("/api/v1/canonical/tipologias")
    assert r.status_code == 200


def test_listar_tipologias_canonicas_tem_campos():
    body = client.get("/api/v1/canonical/tipologias").json()
    assert "total" in body
    assert "tipologias" in body
    assert body["total"] >= 1


def test_detalhe_tipologia_canonica_404():
    r = client.get("/api/v1/canonical/tipologias/TIPOLOGIA_INEXISTENTE_9999")
    assert r.status_code == 404


# ── /api/v1/canonical/modelos ─────────────────────────────────────────────────

def test_listar_modelos_canonicos_200():
    r = client.get("/api/v1/canonical/modelos")
    assert r.status_code == 200


def test_listar_modelos_canonicos_tem_campos():
    body = client.get("/api/v1/canonical/modelos").json()
    assert "total" in body
    assert "modelos" in body
    assert body["total"] >= 1


# ── /api/v1/canonical/ferragens ───────────────────────────────────────────────

def test_listar_ferragens_canonicas_200():
    r = client.get("/api/v1/canonical/ferragens")
    assert r.status_code == 200


def test_listar_ferragens_canonicas_tem_campos():
    body = client.get("/api/v1/canonical/ferragens").json()
    assert "total" in body
    assert "ferragens" in body


# ── /api/v1/canonical/etl/auditoria ──────────────────────────────────────────

def test_auditoria_200():
    r = client.get("/api/v1/canonical/etl/auditoria")
    assert r.status_code == 200


def test_auditoria_tem_registros():
    body = client.get("/api/v1/canonical/etl/auditoria").json()
    assert body["total"] >= 7
