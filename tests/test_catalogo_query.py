"""Testes dos endpoints /api/v1/catalogo-pdf/* — Sprint 9."""
import json
import os
import tempfile
import pytest

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

_FAB = "FAB_QTEST_9701"
_CODIGO = "QT-001"
_CODIGO_NORM = "QT001"


@pytest.fixture(scope="module", autouse=True)
def _seed_catalogo_data():
    """Garante ao menos um fabricante e puxador de teste no DB."""
    produtos = [
        {
            "codigo": _CODIGO,
            "nome": "Puxador Query Test",
            "tipo_visual": "barra",
            "dimensoes_mm": {"comprimento": 300, "diametro": 12},
            "material": "aco inox",
            "acabamento": "polido",
            "fabricante": _FAB,
            "pagina_origem": 1,
        }
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"produtos": produtos, "total_produtos": 1}, f, ensure_ascii=False)
        fpath = f.name
    from app.services.catalogo_importer import importar_catalogo_arquivo
    importar_catalogo_arquivo(fpath)
    os.unlink(fpath)


# ── /api/v1/catalogo-pdf/fabricantes ─────────────────────────────────────────

def test_listar_fabricantes_200():
    r = client.get("/api/v1/catalogo-pdf/fabricantes")
    assert r.status_code == 200


def test_listar_fabricantes_tem_campos():
    body = client.get("/api/v1/catalogo-pdf/fabricantes").json()
    assert "total" in body
    assert "fabricantes" in body
    assert body["total"] >= 1


def test_fabricante_semeado_presente():
    body = client.get("/api/v1/catalogo-pdf/fabricantes").json()
    codigos = [f["codigo"] for f in body["fabricantes"]]
    assert _FAB in codigos


# ── /api/v1/catalogo-pdf/puxadores ───────────────────────────────────────────

def test_listar_puxadores_200():
    r = client.get("/api/v1/catalogo-pdf/puxadores")
    assert r.status_code == 200


def test_listar_puxadores_tem_campos():
    body = client.get("/api/v1/catalogo-pdf/puxadores").json()
    assert "total" in body
    assert "puxadores" in body
    assert "limit" in body
    assert "offset" in body


def test_listar_puxadores_filtro_fabricante():
    r = client.get(f"/api/v1/catalogo-pdf/puxadores?fabricante={_FAB}")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    for p in body["puxadores"]:
        assert p["fabricante_id"] == _FAB


def test_listar_puxadores_filtro_tipo_visual():
    r = client.get("/api/v1/catalogo-pdf/puxadores?tipo_visual=barra")
    assert r.status_code == 200


def test_listar_puxadores_filtro_comp_range():
    r = client.get("/api/v1/catalogo-pdf/puxadores?comp_min=200&comp_max=400")
    assert r.status_code == 200
    body = r.json()
    for p in body["puxadores"]:
        if p["comp_mm"] is not None:
            assert 200 <= p["comp_mm"] <= 400


def test_listar_puxadores_paginacao():
    r = client.get("/api/v1/catalogo-pdf/puxadores?limit=3&offset=0")
    body = r.json()
    assert len(body["puxadores"]) <= 3


# ── /api/v1/catalogo-pdf/puxadores/buscar/{codigo} ───────────────────────────

def test_buscar_codigo_existente():
    r = client.get(f"/api/v1/catalogo-pdf/puxadores/buscar/{_CODIGO}")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert body["puxadores"][0]["codigo"] == _CODIGO


def test_buscar_codigo_normalizado():
    r = client.get(f"/api/v1/catalogo-pdf/puxadores/buscar/qt-001")
    assert r.status_code == 200


def test_buscar_codigo_inexistente_404():
    r = client.get("/api/v1/catalogo-pdf/puxadores/buscar/CODIGO_INEXISTENTE_99999")
    assert r.status_code == 404


# ── /api/v1/catalogo-pdf/stats ────────────────────────────────────────────────

def test_stats_200():
    r = client.get("/api/v1/catalogo-pdf/stats")
    assert r.status_code == 200


def test_stats_campos():
    body = client.get("/api/v1/catalogo-pdf/stats").json()
    assert "total_produtos" in body
    assert "por_fabricante" in body
    assert "por_tipo_visual" in body
    assert body["total_produtos"] >= 1


# ── /api/v1/catalogo-pdf/sugerir ──────────────────────────────────────────────

def test_sugerir_200():
    r = client.get("/api/v1/catalogo-pdf/sugerir?tipo_visual=barra&comp_mm=300")
    assert r.status_code == 200


def test_sugerir_retorna_sugestoes():
    body = client.get("/api/v1/catalogo-pdf/sugerir?tipo_visual=barra").json()
    assert "sugestoes" in body
