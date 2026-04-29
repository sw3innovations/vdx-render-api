"""Tests for _load_ferragens_render integration — Sprint 10 Complemento."""
import os
import json
import pytest

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")


@pytest.fixture(scope="module")
def render_stats():
    from app.core.constitution import _get_conn
    from app.etl.loaders.load_canonical import CanonicalLoader
    with CanonicalLoader() as loader:
        loader.reset()
        return loader.run()


def test_popular_ferragens_render_migra_161(render_stats):
    """161 render ferragens processed: new rows + fused rows = 161."""
    total = render_stats.ferragens_render + render_stats.ferragens_fundidas
    assert total == 161


def test_fundir_codigo_existente_no_pdf_atualiza_fontes_json(render_stats):
    from app.core.constitution import _get_conn
    conn = _get_conn()
    # Any record fused from both sources must list both "catalogo_pdf" and "render"
    row = conn.execute(
        "SELECT fontes_json FROM ferragens_canonicas WHERE fontes_json LIKE '%render%' AND fontes_json LIKE '%catalogo_pdf%' LIMIT 1"
    ).fetchone()
    conn.close()
    assert row is not None, "Nenhum registro fundido encontrado"
    fontes = json.loads(row[0])
    assert "catalogo_pdf" in fontes
    assert "render" in fontes


def test_codigo_novo_do_render_cria_canonico(render_stats):
    assert render_stats.ferragens_render >= 50


def test_alias_criado_do_codigo_original(render_stats):
    from app.core.constitution import _get_conn
    conn = _get_conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM ferragens_aliases WHERE fonte = 'render'"
    ).fetchone()[0]
    conn.close()
    assert count >= 161


def test_equivalencias_viram_aliases(render_stats):
    from app.core.constitution import _get_conn
    conn = _get_conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM ferragens_aliases WHERE fonte LIKE 'equivalencias_%'"
    ).fetchone()[0]
    conn.close()
    assert count >= 1


def test_material_inferido_de_nome_dobradica(render_stats):
    from app.core.constitution import _get_conn
    conn = _get_conn()
    # At least some dobradiças/pivots should have a material resolved (zamak, aço, etc.)
    row = conn.execute(
        """SELECT COUNT(*) FROM ferragens_canonicas
           WHERE fontes_json LIKE '%render%'
           AND material_id IS NOT NULL"""
    ).fetchone()
    conn.close()
    assert row[0] >= 1


def test_idempotencia_re_executar_nao_duplica(render_stats):
    from app.core.constitution import _get_conn
    from app.etl.loaders.load_canonical import CanonicalLoader
    conn = _get_conn()
    before = conn.execute("SELECT COUNT(*) FROM ferragens_canonicas").fetchone()[0]
    conn.close()

    with CanonicalLoader() as loader:
        loader.run()

    conn = _get_conn()
    after = conn.execute("SELECT COUNT(*) FROM ferragens_canonicas").fetchone()[0]
    conn.close()
    assert after == before


def test_total_canonicas_apos_render_e_pdf_aproximadamente_445(render_stats):
    from app.core.constitution import _get_conn
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM ferragens_canonicas").fetchone()[0]
    conn.close()
    assert 300 <= total <= 500, f"Total inesperado: {total}"


def test_fusao_tipos_diferentes_por_codigo(render_stats):
    """Fusion must happen when codigo_normalizado matches, even if tipo differs."""
    from app.core.constitution import _get_conn
    conn = _get_conn()
    # At least some canonical records must carry both catalogo_pdf and render as sources
    fused_db = conn.execute(
        "SELECT COUNT(*) FROM ferragens_canonicas WHERE fontes_json LIKE '%render%' AND fontes_json LIKE '%catalogo_pdf%'"
    ).fetchone()[0]
    conn.close()
    # render-to-pdf fusions happened (stat includes render-to-render duplicates too)
    assert render_stats.ferragens_fundidas > 0
    assert fused_db > 0
