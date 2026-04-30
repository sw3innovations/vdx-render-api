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


# ── Sprint 11 Fase 1 — tem_renderer ───────────────────────────────────────────

def test_canonical_tipologias_inclui_campo_tem_renderer():
    body = client.get("/api/v1/canonical/tipologias?limit=200").json()
    assert "tipologias" in body
    assert len(body["tipologias"]) > 0
    for t in body["tipologias"]:
        assert "tem_renderer" in t, f"tem_renderer ausente em {t.get('codigo')}"
        assert isinstance(t["tem_renderer"], bool)


def test_tem_renderer_true_para_porta_abrir():
    r = client.get("/api/v1/canonical/tipologias/porta_abrir")
    assert r.status_code == 200, f"porta_abrir não encontrada (status {r.status_code})"
    body = r.json()
    assert body.get("tem_renderer") is True


def test_tem_renderer_false_para_sanfonado_sem_schema():
    r = client.get("/api/v1/canonical/tipologias/TIP_0015_SANFONADO")
    assert r.status_code == 200, "TIP_0015_SANFONADO não encontrada nas tipologias canonicas"
    body = r.json()
    assert body.get("tem_renderer") is False


# ── Sprint 11 Fase 2 — ferragens canônicas (filtros, busca) ───────────────────

def test_canonical_ferragens_filtra_por_tipo_puxador():
    body = client.get("/api/v1/canonical/ferragens?tipo=puxador&limit=200").json()
    assert body["total"] >= 1
    _PUXADOR_TIPOS = {"puxador", "barra", "bola", "h", "u", "concha", "capsula"}
    for f in body["ferragens"]:
        assert f["tipo"] in _PUXADOR_TIPOS, f"tipo inesperado: {f['tipo']}"


def test_canonical_ferragens_inclui_fabricante_nome():
    body = client.get("/api/v1/canonical/ferragens?tipo=puxador&limit=5").json()
    assert body["total"] >= 1
    first = body["ferragens"][0]
    assert "fabricante_nome" in first


def test_canonical_ferragens_filtra_por_fabricante():
    body = client.get("/api/v1/canonical/ferragens?fabricante=SM").json()
    for f in body["ferragens"]:
        assert f["fabricante_codigo"] == "SM"


def test_canonical_ferragens_filtra_por_subtipo_barra():
    body = client.get("/api/v1/canonical/ferragens?subtipo=barra&limit=100").json()
    assert body["total"] >= 1
    for f in body["ferragens"]:
        assert f["tipo"] == "barra"


def test_canonical_ferragens_filtra_por_comprimento_range():
    body = client.get("/api/v1/canonical/ferragens?comp_min=300&comp_max=400&limit=100").json()
    for f in body["ferragens"]:
        if f["comprimento_mm"] is not None:
            assert 300 <= f["comprimento_mm"] <= 400


def test_canonical_ferragens_busca_textual():
    body = client.get("/api/v1/canonical/ferragens?busca=Puxador&limit=50").json()
    assert body["total"] >= 1
    for f in body["ferragens"]:
        assert "Puxador" in f["nome_apresentacao"] or "puxador" in f["nome_apresentacao"].lower()


def test_canonical_ferragens_filtros_endpoint():
    r = client.get("/api/v1/canonical/ferragens/filtros?tipo=puxador")
    assert r.status_code == 200
    body = r.json()
    assert "fabricantes" in body
    assert "subtipos" in body
    assert "comprimento_min" in body
    assert "comprimento_max" in body
    assert len(body["fabricantes"]) >= 1
    for fab in body["fabricantes"]:
        assert not fab["id"].startswith("TEST_"), f"Fabricante de teste no filtros: {fab['id']}"
        assert not fab["id"].startswith("FAB_"), f"Fabricante de teste no filtros: {fab['id']}"


# ── Sprint 11 Fase 3 — dobradica / fechadura / suporte ────────────────────────

def test_canonical_ferragens_filtra_por_tipo_dobradica():
    body = client.get("/api/v1/canonical/ferragens?tipo=dobradica&limit=100").json()
    assert body["total"] >= 1
    _DOBRADICA_TIPOS = {"dobradica", "dobradica_basculante", "dobradica_batente", "dobradica_box"}
    for f in body["ferragens"]:
        assert f["tipo"] in _DOBRADICA_TIPOS, f"tipo inesperado: {f['tipo']}"


def test_canonical_ferragens_filtros_dobradica():
    r = client.get("/api/v1/canonical/ferragens/filtros?tipo=dobradica")
    assert r.status_code == 200
    body = r.json()
    assert "fabricantes" in body and "subtipos" in body
    assert len(body["fabricantes"]) >= 1
    for fab in body["fabricantes"]:
        assert not fab["id"].startswith("TEST_")
        assert not fab["id"].startswith("FAB_")


def test_canonical_ferragens_filtra_por_tipo_fechadura():
    body = client.get("/api/v1/canonical/ferragens?tipo=fechadura&limit=100").json()
    assert body["total"] >= 1
    for f in body["ferragens"]:
        assert f["tipo"] == "fechadura"


def test_canonical_ferragens_filtros_fechadura():
    r = client.get("/api/v1/canonical/ferragens/filtros?tipo=fechadura")
    assert r.status_code == 200
    body = r.json()
    assert "fabricantes" in body
    assert len(body["fabricantes"]) >= 1


def test_canonical_ferragens_filtra_por_tipo_suporte():
    body = client.get("/api/v1/canonical/ferragens?tipo=suporte&limit=100").json()
    assert body["total"] >= 1
    for f in body["ferragens"]:
        assert f["tipo"] == "suporte"


def test_canonical_ferragens_filtros_suporte():
    r = client.get("/api/v1/canonical/ferragens/filtros?tipo=suporte")
    assert r.status_code == 200
    body = r.json()
    assert "fabricantes" in body
    assert len(body["fabricantes"]) >= 1
