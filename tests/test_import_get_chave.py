"""Tests for GET /api/v1/import/{chave} — Sprint 11.1."""
import os
import pytest

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

_PAYLOAD = {
    "nome": "Porta Teste 11.1",
    "categoria": "porta",
    "paineis": [{"nome": "Folha", "largura_mm": 900, "altura_mm": 2100}],
    "opcoes": {"cor": "incolor", "acabamento": "cromado", "incluir_png": False, "incluir_pdf": False, "incluir_3d": False},
}


@pytest.fixture(scope="module")
def chave_importada():
    r = client.post("/api/v1/import/tipologia", json=_PAYLOAD)
    assert r.status_code == 200
    return r.json()["tipologia_chave"]


def test_post_import_persiste_manifest_em_disco(chave_importada):
    from pathlib import Path
    manifest_path = Path("uploads/import") / chave_importada / "manifest.json"
    assert manifest_path.exists(), f"manifest.json not found at {manifest_path}"


def test_get_import_chave_existente_retorna_manifest(chave_importada):
    r = client.get(f"/api/v1/import/{chave_importada}")
    assert r.status_code == 200
    body = r.json()
    assert body["tipologia_chave"] == chave_importada
    assert "svg" in body
    assert "ferragens_resolvidas" in body


def test_get_import_chave_inexistente_retorna_404():
    r = client.get("/api/v1/import/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
