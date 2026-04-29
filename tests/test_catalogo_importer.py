"""Testes do CatalogoImporter — Sprint 9."""
import json
import os
import tempfile
import pytest

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

_CATALOG_DIR = os.path.expanduser("~/Downloads")


def _count(table: str) -> int:
    from app.core.constitution import _get_conn
    conn = _get_conn()
    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return n


def _make_catalog_file(produtos: list[dict]) -> str:
    """Grava produtos num arquivo JSON temporário e retorna o caminho."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"produtos": produtos, "total_produtos": len(produtos)}, f, ensure_ascii=False)
        return f.name


# ── normalizar_codigo ─────────────────────────────────────────────────────────

def test_normalizar_codigo_remove_espacos_e_hifens():
    from app.services.catalogo_importer import _normalizar_codigo
    assert _normalizar_codigo("P ARCO-500") == "PARCO500"


def test_normalizar_codigo_remove_barra():
    from app.services.catalogo_importer import _normalizar_codigo
    assert _normalizar_codigo("01.24/026") == "01.24026"


def test_normalizar_codigo_uppercase():
    from app.services.catalogo_importer import _normalizar_codigo
    assert _normalizar_codigo("abc-123") == "ABC123"


def test_normalizar_codigo_none_retorna_none():
    from app.services.catalogo_importer import _normalizar_codigo
    assert _normalizar_codigo(None) is None


def test_normalizar_codigo_vazio_retorna_none():
    from app.services.catalogo_importer import _normalizar_codigo
    assert _normalizar_codigo("") is None


# ── importar_catalogo_arquivo ─────────────────────────────────────────────────

def test_importar_arquivo_retorna_stats():
    from app.services.catalogo_importer import importar_catalogo_arquivo
    produtos = [
        {
            "codigo": "TEST-001",
            "nome": "Puxador Teste",
            "tipo_visual": "barra",
            "dimensoes_mm": {"comprimento": 300, "diametro": 12},
            "material": "aco inox",
            "acabamento": "polido",
            "fabricante": "TEST_FAB_UNIT",
            "pagina_origem": 1,
        }
    ]
    path = _make_catalog_file(produtos)
    try:
        stats = importar_catalogo_arquivo(path)
        assert stats["produtos"] == 1
        assert "TEST_FAB_UNIT" in stats.get("arquivo", "") or stats["produtos"] == 1
    finally:
        os.unlink(path)


def test_importar_arquivo_idempotente():
    from app.services.catalogo_importer import importar_catalogo_arquivo
    produtos = [
        {
            "codigo": "IDEM-001",
            "nome": "Puxador Idem",
            "tipo_visual": "barra",
            "dimensoes_mm": {"comprimento": 200},
            "fabricante": "TEST_FAB_IDEM",
            "pagina_origem": 1,
        }
    ]
    path = _make_catalog_file(produtos)
    try:
        importar_catalogo_arquivo(path)
        antes = _count("catalogo_puxadores")
        importar_catalogo_arquivo(path)
        assert _count("catalogo_puxadores") == antes
    finally:
        os.unlink(path)


def test_importar_arquivo_cria_fabricante():
    from app.core.constitution import _get_conn
    from app.services.catalogo_importer import importar_catalogo_arquivo
    produtos = [
        {
            "codigo": "F001",
            "nome": "Puxador F",
            "tipo_visual": "bola",
            "dimensoes_mm": {"diametro": 18},
            "fabricante": "FAB_NOVO_9901",
            "pagina_origem": 1,
        }
    ]
    path = _make_catalog_file(produtos)
    try:
        importar_catalogo_arquivo(path)
        conn = _get_conn()
        row = conn.execute("SELECT codigo FROM catalogo_fabricantes WHERE codigo='FAB_NOVO_9901'").fetchone()
        conn.close()
        assert row is not None
    finally:
        os.unlink(path)


def test_importar_arquivo_campos_dimensoes():
    from app.core.constitution import _get_conn
    from app.services.catalogo_importer import importar_catalogo_arquivo
    produtos = [
        {
            "codigo": "DIM-TEST-9901",
            "nome": "Teste Dimensoes",
            "tipo_visual": "capsula",
            "dimensoes_mm": {
                "comprimento": 150,
                "diametro": 20,
                "distancia_entre_furos": 100,
            },
            "material": "aluminio",
            "acabamento": "anodizado",
            "fabricante": "FAB_DIM_TEST",
            "pagina_origem": 2,
        }
    ]
    path = _make_catalog_file(produtos)
    try:
        importar_catalogo_arquivo(path)
        conn = _get_conn()
        row = conn.execute(
            "SELECT comp_mm, diametro_mm, distancia_furos_mm, material, acabamento "
            "FROM catalogo_puxadores WHERE codigo_normalizado='DIMTEST9901'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 150
        assert row[1] == 20
        assert row[2] == 100
        assert row[3] == "aluminio"
        assert row[4] == "anodizado"
    finally:
        os.unlink(path)


# ── integração com arquivos reais ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def catalogo_importado():
    """Importa todos os catálogos reais uma vez."""
    import glob
    arquivos = glob.glob(os.path.join(_CATALOG_DIR, "extraido_*.json"))
    if not arquivos:
        pytest.skip(f"Nenhum catálogo encontrado em: {_CATALOG_DIR}")
    from app.services.catalogo_importer import importar_catalogos
    return importar_catalogos(_CATALOG_DIR)


def test_catalogo_importou_arquivos(catalogo_importado):
    assert len(catalogo_importado["arquivos"]) >= 1


def test_catalogo_importou_mais_de_200_produtos(catalogo_importado):
    assert catalogo_importado["total_produtos"] >= 200


def test_catalogo_importou_fabricantes(catalogo_importado):
    from app.core.constitution import _get_conn
    conn = _get_conn()
    n = conn.execute("SELECT COUNT(*) FROM catalogo_fabricantes").fetchone()[0]
    conn.close()
    assert n >= 3


def test_catalogo_idempotente(catalogo_importado):
    antes = _count("catalogo_puxadores")
    from app.services.catalogo_importer import importar_catalogos
    importar_catalogos(_CATALOG_DIR)
    assert _count("catalogo_puxadores") == antes


def test_catalogo_tabelas_existem_no_db():
    from app.core.constitution import _get_conn
    conn = _get_conn()
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    for t in ["catalogo_fabricantes", "catalogo_puxadores", "catalogo_puxador_equivalencias"]:
        assert t in tables, f"Tabela {t} não encontrada"
