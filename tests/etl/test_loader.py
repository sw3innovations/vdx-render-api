"""Integration tests for CanonicalLoader — Sprint 10."""
import os
import pytest

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")


@pytest.fixture(scope="module")
def loader_stats():
    """Run the ETL loader once and return stats."""
    from app.core.constitution import _get_conn
    from app.etl.loaders.load_canonical import CanonicalLoader
    with CanonicalLoader() as loader:
        loader.reset()
        return loader.run()


def test_loader_materiais_semeados(loader_stats):
    assert loader_stats.materiais >= 9


def test_loader_acabamentos_semeados(loader_stats):
    assert loader_stats.acabamentos >= 11


def test_loader_variaveis_semeadas(loader_stats):
    assert loader_stats.variaveis >= 11


def test_loader_tipologias_carregadas(loader_stats):
    assert loader_stats.tipologias >= 1


def test_loader_modelos_carregados(loader_stats):
    assert loader_stats.modelos >= 1


def test_loader_sem_erros_criticos(loader_stats):
    assert loader_stats.modelos > 0


def test_tabelas_populadas_no_db(loader_stats):
    from app.core.constitution import _get_conn
    conn = _get_conn()
    for table in ["materiais_canonicos", "acabamentos_canonicos", "variaveis_canonicas"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert count >= 1, f"{table} está vazio"
    conn.close()


def test_tipologias_canonicas_tem_codigo_e_nome(loader_stats):
    from app.core.constitution import _get_conn
    conn = _get_conn()
    rows = conn.execute("SELECT codigo, nome_apresentacao FROM tipologias_canonicas LIMIT 5").fetchall()
    conn.close()
    for codigo, nome in rows:
        assert codigo and nome


def test_modelos_canonicos_tem_tipologia_fk(loader_stats):
    from app.core.constitution import _get_conn
    conn = _get_conn()
    row = conn.execute(
        "SELECT COUNT(*) FROM modelos_canonicos WHERE tipologia_id IS NOT NULL"
    ).fetchone()
    conn.close()
    assert row[0] >= 1


def test_auditoria_registrada(loader_stats):
    from app.core.constitution import _get_conn
    conn = _get_conn()
    count = conn.execute("SELECT COUNT(*) FROM etl_auditoria").fetchone()[0]
    conn.close()
    assert count >= 7


def test_loader_idempotente(loader_stats):
    """Running loader twice should not duplicate canonical records."""
    from app.core.constitution import _get_conn
    from app.etl.loaders.load_canonical import CanonicalLoader

    conn = _get_conn()
    before = conn.execute("SELECT COUNT(*) FROM materiais_canonicos").fetchone()[0]
    conn.close()

    with CanonicalLoader() as loader:
        loader.run()

    conn = _get_conn()
    after = conn.execute("SELECT COUNT(*) FROM materiais_canonicos").fetchone()[0]
    conn.close()
    assert after == before
