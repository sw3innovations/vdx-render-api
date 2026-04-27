"""
Testes para app/routers/catalogo.py — endpoints públicos de ferragens e kits.

Usa DB SQLite em memória para independência do ambiente (CI não tem o DB de produção).
"""
import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")


# ─── Fixture: DB em memória com dados representativos ─────────────────────────

_FERRAGENS_TEST = [
    # (codigo, codigo_norm, fabricante_id, nome, tipo, material, espessura_vidro)
    ("AL1629A",  "1629A", "AL", "Puxador 18mm Diâmetro",        "puxador",    "Inox",  "[8, 10]"),
    ("AL1629B",  "1629B", "AL", "Puxador 25mm Diâmetro",        "puxador",    "Inox",  None),
    ("HE1629A",  "1629A", "HE", "Puxador 18mm para box",        "puxador",    "Zamac", None),
    ("SM1520",   "1520",  "SM", "Fechadura Central 1520",        "fechadura",  "Zamac", None),
    ("SM1521",   "1521",  "SM", "Fechadura Superior 1521",       "fechadura",  "Zamac", None),
    ("SM1101",   "1101",  "SM", "Dobradiça Superior 1101",       "dobradica",  "Zamac", None),
    ("SM1103",   "1103",  "SM", "Dobradiça Inferior 1103",       "dobradica",  "Zamac", None),
    ("AL1201",   "1201",  "AL", "Pivô Superior",                 "pivo",       "Zamac", None),
    ("AL1013",   "1013",  "AL", "Pivô Inferior",                 "pivo",       "Zamac", None),
    ("SM2001",   "2001",  "SM", "Roldana Simples",               "roldana",    "Nylon", None),
]

# AL1629A e HE1629A compartilham codigo_normalizado "1629A" → 9 grupos
_EXPECTED_GROUPS = 9

_KITS_TEST = [
    # (id, numero, fabricante_id, nome, linha, max_vao_json, acabamentos_json)
    (1, "01", "SM", "Porta Simples Pivotante",   None,       '{"opcao1":"900x2200mm"}',              None),
    (2, "02", "AL", "Porta Correr 2 Folhas",     "Polímero", None, '["Cromado","Inox"]'),
    (3, "03", "HE", "Janela Basculante",         None,       None, None),
    (4, "08", "SM", "Porta Dupla Pivotante",     None,       None, None),
]

_KIT_COMPONENTES_TEST = [
    # (kit_id, ferragem_codigo, quantidade, posicao, nome)
    (1, "AL1201", 1, "superior", "Pivô Superior"),
    (1, "AL1013", 1, "inferior", "Pivô Inferior"),
    (1, "SM1520", 1, None,       "Fechadura Central"),
    (2, "SM2001", 4, None,       "Roldana"),
    (2, "SM1520", 2, None,       "Fechadura"),
]


@pytest.fixture
def test_db(tmp_path):
    """Cria um DB SQLite em memória com dados representativos."""
    db_path = tmp_path / "test_constitution.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE ferragens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT, codigo_normalizado TEXT, fabricante_id TEXT,
            nome TEXT, tipo TEXT, material TEXT,
            dimensoes_json TEXT, espessura_vidro TEXT, cores_json TEXT,
            pagina_catalogo INTEGER, confianca REAL, fonte TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO ferragens (codigo, codigo_normalizado, fabricante_id, nome, tipo, material, espessura_vidro) VALUES (?,?,?,?,?,?,?)",
        _FERRAGENS_TEST,
    )
    conn.execute("""
        CREATE TABLE kits (
            id INTEGER PRIMARY KEY, numero TEXT, fabricante_id TEXT,
            nome TEXT, linha TEXT, max_vao_json TEXT, acabamentos_json TEXT,
            pagina_catalogo INTEGER
        )
    """)
    conn.executemany(
        "INSERT INTO kits (id, numero, fabricante_id, nome, linha, max_vao_json, acabamentos_json) VALUES (?,?,?,?,?,?,?)",
        _KITS_TEST,
    )
    conn.execute("""
        CREATE TABLE kit_componentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kit_id INTEGER, ferragem_codigo TEXT, quantidade INTEGER,
            posicao TEXT, nome TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO kit_componentes (kit_id, ferragem_codigo, quantidade, posicao, nome) VALUES (?,?,?,?,?)",
        _KIT_COMPONENTES_TEST,
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def client(test_db):
    from app.main import app
    with patch("app.routers.catalogo._DB_PATH", test_db):
        yield TestClient(app)


# ─── Ferragens — estrutura agrupada ──────────────────────────────────────────

def test_listar_todas_ferragens_retorna_lista(client):
    res = client.get("/api/v1/catalogo/ferragens")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == _EXPECTED_GROUPS


def test_estrutura_ferragem_tem_campos_esperados(client):
    res = client.get("/api/v1/catalogo/ferragens")
    assert res.status_code == 200
    item = res.json()[0]
    for campo in ("codigo_normalizado", "nome", "tipo", "fabricantes"):
        assert campo in item, f"Campo '{campo}' ausente na resposta"


def test_total_grupos_menor_que_total_registros(client):
    res = client.get("/api/v1/catalogo/ferragens")
    assert res.status_code == 200
    assert len(res.json()) < len(_FERRAGENS_TEST)


def test_grupo_multi_fabricante_tem_dois_fabricantes(client):
    res = client.get("/api/v1/catalogo/ferragens?tipo=puxador")
    assert res.status_code == 200
    grupos = res.json()
    grupo_1629a = next((g for g in grupos if g["codigo_normalizado"] == "1629A"), None)
    assert grupo_1629a is not None
    assert len(grupo_1629a["fabricantes"]) == 2


def test_grupo_single_fabricante_tem_um_fabricante(client):
    res = client.get("/api/v1/catalogo/ferragens?tipo=puxador")
    assert res.status_code == 200
    grupos = res.json()
    grupo_1629b = next((g for g in grupos if g["codigo_normalizado"] == "1629B"), None)
    assert grupo_1629b is not None
    assert len(grupo_1629b["fabricantes"]) == 1


def test_fabricante_estrutura_tem_campos_esperados(client):
    res = client.get("/api/v1/catalogo/ferragens?tipo=puxador")
    assert res.status_code == 200
    fabricante = res.json()[0]["fabricantes"][0]
    for campo in ("id", "codigo", "material", "espessura_vidro"):
        assert campo in fabricante, f"Campo '{campo}' ausente no fabricante"


def test_espessura_vidro_retorna_array_de_inteiros(client):
    res = client.get("/api/v1/catalogo/ferragens?tipo=puxador")
    assert res.status_code == 200
    grupos = res.json()
    grupo_1629a = next(g for g in grupos if g["codigo_normalizado"] == "1629A")
    fab_al = next(f for f in grupo_1629a["fabricantes"] if f["id"] == "AL")
    assert isinstance(fab_al["espessura_vidro"], list)
    assert fab_al["espessura_vidro"] == [8, 10]


def test_espessura_vidro_null_retorna_lista_vazia(client):
    res = client.get("/api/v1/catalogo/ferragens?tipo=puxador")
    assert res.status_code == 200
    grupos = res.json()
    grupo_1629b = next(g for g in grupos if g["codigo_normalizado"] == "1629B")
    assert grupo_1629b["fabricantes"][0]["espessura_vidro"] == []


# ─── Ferragens — filtros ──────────────────────────────────────────────────────

def test_listar_ferragens_filtro_tipo_puxador(client):
    res = client.get("/api/v1/catalogo/ferragens?tipo=puxador")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2  # 2 grupos: "1629A" e "1629B"
    for item in data:
        assert item["tipo"] == "puxador"


def test_listar_ferragens_filtro_tipo_case_insensitive(client):
    res_lower = client.get("/api/v1/catalogo/ferragens?tipo=puxador")
    res_upper = client.get("/api/v1/catalogo/ferragens?tipo=PUXADOR")
    assert res_lower.status_code == 200
    assert res_upper.status_code == 200
    assert len(res_lower.json()) == len(res_upper.json())


def test_listar_ferragens_filtro_tipo_invalido_retorna_lista_vazia(client):
    res = client.get("/api/v1/catalogo/ferragens?tipo=tipo_inexistente_xyz")
    assert res.status_code == 200
    assert res.json() == []


def test_listar_ferragens_filtro_fabricante(client):
    res = client.get("/api/v1/catalogo/ferragens?fabricante=SM")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    for grupo in data:
        for fab in grupo["fabricantes"]:
            assert fab["id"] == "SM"


def test_listar_ferragens_por_tipo_path(client):
    res = client.get("/api/v1/catalogo/ferragens/puxador")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
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
    assert len(data) == len(_KITS_TEST)


def test_estrutura_kit_tem_campos_esperados(client):
    res = client.get("/api/v1/catalogo/kits")
    assert res.status_code == 200
    kit = res.json()[0]
    for campo in ("id", "numero", "nome", "fabricante_id", "componentes"):
        assert campo in kit, f"Campo '{campo}' ausente no kit"


def test_kit_tem_componentes(client):
    res = client.get("/api/v1/catalogo/kits")
    assert res.status_code == 200
    kit1 = next(k for k in res.json() if k["id"] == 1)
    assert len(kit1["componentes"]) == 3


def test_listar_kits_por_tipologia_porta_pivotante(client):
    res = client.get("/api/v1/catalogo/kits/porta_pivotante_simples")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    nomes = [k["nome"].lower() for k in data]
    assert any("pivotante" in n for n in nomes)


def test_listar_kits_filtro_tipologia_query_param(client):
    res = client.get("/api/v1/catalogo/kits?tipologia=porta_pivotante_simples")
    assert res.status_code == 200
    assert len(res.json()) > 0


def test_listar_kits_tipologia_inexistente_retorna_404(client):
    res = client.get("/api/v1/catalogo/kits/tipologia_completamente_inexistente_xyz")
    assert res.status_code == 404


def test_componente_estrutura(client):
    res = client.get("/api/v1/catalogo/kits")
    assert res.status_code == 200
    kit1 = next(k for k in res.json() if k["id"] == 1)
    comp = kit1["componentes"][0]
    for campo in ("ferragem_codigo", "quantidade", "nome"):
        assert campo in comp
