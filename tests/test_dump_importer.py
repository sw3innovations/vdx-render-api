"""Testes do DumpImporter — Sprint 9."""
import os
import pytest

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

_DUMP_DIR = "/tmp/vdx_dump_v2/extracao"


def _count(table: str) -> int:
    from app.core.constitution import _get_conn
    conn = _get_conn()
    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return n


# ── unit tests com dados inline ───────────────────────────────────────────────

def _fetch_one(table: str, pk_col: str, pk_val) -> tuple | None:
    from app.core.constitution import _get_conn
    conn = _get_conn()
    row = conn.execute(f"SELECT * FROM {table} WHERE {pk_col}=?", (pk_val,)).fetchone()
    conn.close()
    return row


def test_importar_tipologias_inline():
    from app.core.constitution import _get_conn
    from app.services.dump_importer import _importar_tipologias
    conn = _get_conn()
    rows = [{"NU_TMD": 9901, "DS_TMD": "TESTE TIPOLOGIA", "ID_ATIVO": "S", "SACADA": "N"}]
    n = _importar_tipologias(conn, rows)
    conn.commit()
    conn.close()
    assert n == 1
    assert _fetch_one("dump_tipologias", "nu_tip", 9901) is not None


def test_importar_tipologias_idempotente():
    from app.core.constitution import _get_conn
    from app.services.dump_importer import _importar_tipologias
    rows = [{"NU_TMD": 9902, "DS_TMD": "IDEMPOTENTE", "ID_ATIVO": "S", "SACADA": "N"}]
    conn = _get_conn()
    _importar_tipologias(conn, rows)
    conn.commit()
    conn.close()
    antes = _count("dump_tipologias")
    conn = _get_conn()
    _importar_tipologias(conn, rows)
    conn.commit()
    conn.close()
    assert _count("dump_tipologias") == antes


def test_importar_modelos_inline():
    from app.core.constitution import _get_conn
    from app.services.dump_importer import _importar_modelos
    conn = _get_conn()
    modelos_dict = {
        "9901": {"DS_MOD": "MODELO TESTE", "NU_TMD": None, "DIV_LARGURA": 2, "DIV_ALTURA": 1}
    }
    n = _importar_modelos(conn, modelos_dict)
    conn.commit()
    conn.close()
    assert n == 1
    assert _fetch_one("dump_modelos", "nu_mod", 9901) is not None


def test_importar_geometria_pecas_inline():
    from app.core.constitution import _get_conn
    from app.services.dump_importer import _importar_geometria_pecas
    conn = _get_conn()
    rows = [{
        "NU_DMD": 1, "NU_MOD": 9901, "NU_PECA": 1,
        "EIXO_X_ALT": 10.0, "EIXO_Y_ALT": 5.0,
        "EIXO_X_LARG": 20.0, "EIXO_Y_LARG": 8.0,
        "DS_FORMULA_ALT": "ALTURA-10", "DS_FORMULA_LARG": "LARGURA/2",
        "DS_TIPO": "VI", "DS_PECA": "VID", "DS_DESCRICAO": "VIDRO TESTE",
    }]
    n = _importar_geometria_pecas(conn, rows)
    conn.commit()
    conn.close()
    assert n == 1
    from app.core.constitution import _get_conn as gc
    conn2 = gc()
    row = conn2.execute(
        "SELECT ds_formula_alt FROM dump_geometria_pecas WHERE nu_mod=9901 AND nu_peca=1"
    ).fetchone()
    conn2.close()
    assert row is not None and row[0] == "ALTURA-10"


def test_importar_variaveis_altura_inline():
    from app.core.constitution import _get_conn
    from app.services.dump_importer import _importar_variaveis_altura
    conn = _get_conn()
    rows = [{"NU_MDA": 9901, "NU_MOD": 9901, "DS_ALTURA": "ALTURA DO VÃO TESTE", "VAR_ALTURA": 1, "ALTURA_PADRAO": None}]
    n = _importar_variaveis_altura(conn, rows)
    conn.commit()
    conn.close()
    assert n == 1
    assert _fetch_one("dump_variaveis_altura", "nu_mda", 9901) is not None


def test_importar_variaveis_largura_inline():
    from app.core.constitution import _get_conn
    from app.services.dump_importer import _importar_variaveis_largura
    conn = _get_conn()
    rows = [{"NU_MDL": 9901, "NU_MOD": 9901, "DS_LARGURA": "LARGURA DO VÃO TESTE", "VAR_LARGURA": 1, "LARGURA_PADRAO": None}]
    n = _importar_variaveis_largura(conn, rows)
    conn.commit()
    conn.close()
    assert n == 1
    assert _fetch_one("dump_variaveis_largura", "nu_mdl", 9901) is not None


def test_importar_categorias_inline():
    from app.core.constitution import _get_conn
    from app.services.dump_importer import _importar_categorias
    conn = _get_conn()
    rows = [{"NU_CAT": 9901, "DS_CAT": "CATEGORIA TESTE", "ID_ATIVO": "S"}]
    n = _importar_categorias(conn, rows)
    conn.commit()
    conn.close()
    assert n == 1
    assert _fetch_one("dump_categorias_ferragens", "nu_cat", 9901) is not None


# ── integração com arquivos reais ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def dump_importado():
    """Importa o dump completo uma vez para o módulo de testes."""
    import os
    if not os.path.isdir(_DUMP_DIR):
        pytest.skip(f"Diretório de dump não encontrado: {_DUMP_DIR}")
    from app.services.dump_importer import importar_dump
    return importar_dump(_DUMP_DIR)


def test_dump_importou_31_tipologias(dump_importado):
    assert dump_importado["tipologias"] == 31


def test_dump_importou_128_modelos(dump_importado):
    assert dump_importado["modelos"] == 128


def test_dump_importou_471_pecas(dump_importado):
    assert dump_importado["geometria_pecas"] == 471


def test_dump_importou_281_variaveis_altura(dump_importado):
    assert dump_importado["variaveis_altura"] == 281


def test_dump_importou_142_variaveis_largura(dump_importado):
    assert dump_importado["variaveis_largura"] == 142


def test_dump_importou_66_categorias(dump_importado):
    assert dump_importado["categorias"] == 66


def test_dump_idempotente(dump_importado):
    antes = _count("dump_tipologias")
    from app.services.dump_importer import importar_dump
    importar_dump(_DUMP_DIR)
    assert _count("dump_tipologias") == antes


def test_dump_tabelas_existem_no_db():
    from app.core.constitution import _get_conn
    conn = _get_conn()
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    for t in ["dump_tipologias", "dump_modelos", "dump_geometria_pecas",
              "dump_variaveis_altura", "dump_variaveis_largura",
              "dump_categorias_ferragens"]:
        assert t in tables, f"Tabela {t} não encontrada"
