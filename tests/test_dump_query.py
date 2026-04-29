"""Testes dos endpoints /api/v1/dump/* — Sprint 9."""
import os
import pytest

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _seed_dump_data():
    """Garante pelo menos um modelo e tipologia de teste no DB antes dos testes."""
    from app.core.constitution import _get_conn
    from app.services.dump_importer import _importar_tipologias, _importar_modelos, _importar_categorias
    conn = _get_conn()
    _importar_tipologias(conn, [{"NU_TMD": 9801, "DS_TMD": "TIPOLOGIA QUERY TEST", "ID_ATIVO": "S", "SACADA": "N"}])
    _importar_modelos(conn, {"9801": {"DS_MOD": "MODELO QUERY TEST", "NU_TMD": 9801, "DIV_LARGURA": 1, "DIV_ALTURA": 2}})
    _importar_categorias(conn, [{"NU_CAT": 9801, "DS_CAT": "CATEGORIA QUERY TEST", "ID_ATIVO": "S"}])
    conn.commit()
    conn.close()


# ── /api/v1/dump/tipologias ───────────────────────────────────────────────────

def test_listar_tipologias_retorna_200():
    r = client.get("/api/v1/dump/tipologias")
    assert r.status_code == 200


def test_listar_tipologias_tem_campos_esperados():
    r = client.get("/api/v1/dump/tipologias")
    body = r.json()
    assert "total" in body
    assert "tipologias" in body
    assert body["total"] >= 1


def test_listar_tipologias_filtro_ativo():
    r = client.get("/api/v1/dump/tipologias?ativo=S")
    assert r.status_code == 200
    body = r.json()
    for t in body["tipologias"]:
        assert t["id_ativo"] == "S"


def test_detalhe_tipologia_existente():
    r = client.get("/api/v1/dump/tipologias/9801")
    assert r.status_code == 200
    body = r.json()
    assert body["nu_tip"] == 9801
    assert "modelos" in body


def test_detalhe_tipologia_inexistente_404():
    r = client.get("/api/v1/dump/tipologias/99999")
    assert r.status_code == 404


# ── /api/v1/dump/modelos ──────────────────────────────────────────────────────

def test_listar_modelos_retorna_200():
    r = client.get("/api/v1/dump/modelos")
    assert r.status_code == 200


def test_listar_modelos_tem_campos():
    r = client.get("/api/v1/dump/modelos")
    body = r.json()
    assert "total" in body
    assert "modelos" in body
    assert body["total"] >= 1


def test_listar_modelos_filtro_nu_tip():
    r = client.get("/api/v1/dump/modelos?nu_tip=9801")
    assert r.status_code == 200
    body = r.json()
    for m in body["modelos"]:
        assert m["nu_tip"] == 9801


def test_detalhe_modelo_existente_tem_pecas():
    r = client.get("/api/v1/dump/modelos/9801")
    assert r.status_code == 200
    body = r.json()
    assert body["nu_mod"] == 9801
    assert "pecas" in body
    assert "variaveis_altura" in body
    assert "variaveis_largura" in body


def test_detalhe_modelo_inexistente_404():
    r = client.get("/api/v1/dump/modelos/99999")
    assert r.status_code == 404


def test_listar_modelos_paginacao():
    r = client.get("/api/v1/dump/modelos?limit=2&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert len(body["modelos"]) <= 2


# ── /api/v1/dump/geometria ────────────────────────────────────────────────────

def test_listar_geometria_retorna_200():
    r = client.get("/api/v1/dump/geometria")
    assert r.status_code == 200


def test_listar_geometria_tem_campos():
    r = client.get("/api/v1/dump/geometria")
    body = r.json()
    assert "total" in body
    assert "pecas" in body


def test_listar_geometria_filtro_nu_mod():
    r = client.get("/api/v1/dump/geometria?nu_mod=9801")
    assert r.status_code == 200


# ── /api/v1/dump/categorias ───────────────────────────────────────────────────

def test_listar_categorias_retorna_200():
    r = client.get("/api/v1/dump/categorias")
    assert r.status_code == 200


def test_listar_categorias_tem_campos():
    body = client.get("/api/v1/dump/categorias").json()
    assert "total" in body
    assert "categorias" in body
    assert body["total"] >= 1


# ── /api/v1/dump/variaveis ────────────────────────────────────────────────────

def test_listar_variaveis_retorna_200():
    r = client.get("/api/v1/dump/variaveis")
    assert r.status_code == 200


def test_listar_variaveis_filtro_altura():
    r = client.get("/api/v1/dump/variaveis?eixo=altura")
    body = r.json()
    assert "variaveis_altura" in body
    assert "variaveis_largura" not in body


def test_listar_variaveis_filtro_largura():
    r = client.get("/api/v1/dump/variaveis?eixo=largura")
    body = r.json()
    assert "variaveis_largura" in body
    assert "variaveis_altura" not in body
