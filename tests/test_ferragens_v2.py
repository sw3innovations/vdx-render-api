"""Testes para /api/v2/ferragens/* (Phase 6)."""
from __future__ import annotations

import os
os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.constitution import _m010_schema_v2
import app.routers.ferragens_v2 as _v2_mod


# ─── Fixture: DB em memória com dados de teste ───────────────────────────────

def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _m010_schema_v2(conn)

    # Canônicos (1101 tem recorte real; 1114 e 1101R não têm)
    conn.executemany(
        "INSERT INTO canonicas"
        " (canonical_id, linha, categoria, nome_apresentacao, confidence,"
        "  recorte_largura_mm, recorte_altura_mm)"
        " VALUES (?, ?, ?, ?, 'medio', ?, ?)",
        [
            ("1101",  "santa_marina_1000", "dobradica", "Dobradiça Superior 1101", 27.0, 110.0),
            ("1114",  "santa_marina_1000", "dobradica", "Dobradiça 1114",          None, None),
            ("1101R", "santa_marina_1000", "dobradica", "Dobradiça Superior Reforçada", None, None),
        ],
    )

    # Variantes
    conn.executemany(
        "INSERT INTO variantes_canonicas (variant_id, canonical_id, fabricante_codigo, codigo_original)"
        " VALUES (?, ?, ?, ?)",
        [
            ("SM_1101SG", "1101",  "SM",  "1101SG"),
            ("HE_1101",   "1101",  "HE",  "1101"),
            ("SM_1114",   "1114",  "SM",  "1114"),
        ],
    )

    # Aliases
    conn.executemany(
        "INSERT INTO aliases_canonicos (canonical_id, alias, tipo, fonte)"
        " VALUES (?, ?, ?, 'vendedora_niedja')",
        [
            ("1114",  "114",   "truncamento"),
            ("1114",  "1114A", "variant_id"),
            ("1101R", "gv",    "apelido_comercial"),
        ],
    )

    # Kits
    conn.execute(
        "INSERT INTO kits_canonicos (kit_id, nome, tipologia, fabricante_origem)"
        " VALUES ('KIT_TEST_01', 'Kit Teste Porta Correr', 'porta_correr', 'GLP')"
    )
    conn.execute(
        "INSERT INTO kits_componentes (kit_id, canonical_id, quantidade, obrigatorio)"
        " VALUES ('KIT_TEST_01', '1101', 2, 1)"
    )

    # Regras NBR
    conn.execute(
        "INSERT INTO regras_globais (regra_id, categoria, descricao, valor_numerico, unidade, fonte)"
        " VALUES ('NBR_folga_movel_fixo', 'folga_nbr7199', 'Folga padrão móvel-fixo', 3.0, 'mm', 'glasspecas_2022')"
    )

    conn.commit()
    return conn


class _NoCloseConn:
    """Proxy que ignora .close() — mantém o DB aberto entre requests do mesmo teste."""
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
    def __getattr__(self, name: str):
        return getattr(self._conn, name)
    def close(self) -> None:
        pass


@pytest.fixture(autouse=True)
def _patch_conn(monkeypatch):
    """Substitui _get_conn no router v2 pelo DB de teste em memória."""
    _db = _make_db()
    proxy = _NoCloseConn(_db)
    monkeypatch.setattr(_v2_mod, "_get_conn", lambda: proxy)
    yield
    _db.close()


from app.main import app
client = TestClient(app)


# ─── 1. GET /api/v2/ferragens/ ────────────────────────────────────────────────

def test_list_returns_200():
    r = client.get("/api/v2/ferragens/")
    assert r.status_code == 200


def test_list_tem_campos():
    body = client.get("/api/v2/ferragens/").json()
    assert "total" in body
    assert "canonicals" in body
    assert body["total"] == 3


def test_list_filtra_por_linha():
    body = client.get("/api/v2/ferragens/?linha=santa_marina_1000").json()
    assert body["total"] == 3
    for c in body["canonicals"]:
        assert c["linha"] == "santa_marina_1000"


def test_list_filtra_por_categoria():
    body = client.get("/api/v2/ferragens/?categoria=dobradica").json()
    assert body["total"] == 3


def test_list_filtra_por_busca():
    body = client.get("/api/v2/ferragens/?busca=Reforçada").json()
    assert body["total"] == 1
    assert body["canonicals"][0]["canonical_id"] == "1101R"


# ─── 2. GET /api/v2/ferragens/buscar ─────────────────────────────────────────

def test_buscar_por_canonical_id_direto():
    r = client.get("/api/v2/ferragens/buscar?q=1101")
    assert r.status_code == 200
    body = r.json()
    assert body["canonical_id"] == "1101"
    assert body["resolved_from"] is None


def test_buscar_por_alias_truncamento():
    r = client.get("/api/v2/ferragens/buscar?q=114")
    assert r.status_code == 200
    body = r.json()
    assert body["canonical_id"] == "1114"
    assert body["resolved_from"] == "114"


def test_buscar_por_alias_apelido():
    r = client.get("/api/v2/ferragens/buscar?q=gv")
    assert r.status_code == 200
    body = r.json()
    assert body["canonical_id"] == "1101R"
    assert body["resolved_from"] == "gv"


def test_buscar_inclui_variantes():
    body = client.get("/api/v2/ferragens/buscar?q=1101").json()
    assert "variantes" in body
    assert body["total_variantes"] == 2
    codigos = {v["fabricante_codigo"] for v in body["variantes"]}
    assert codigos == {"SM", "HE"}


def test_buscar_inclui_aliases():
    body = client.get("/api/v2/ferragens/buscar?q=1114").json()
    assert "aliases" in body
    assert any(a["alias"] == "114" for a in body["aliases"])


def test_buscar_alias_case_insensitive():
    r = client.get("/api/v2/ferragens/buscar?q=1114a")
    assert r.status_code == 200
    assert r.json()["canonical_id"] == "1114"


def test_buscar_404_para_desconhecido():
    r = client.get("/api/v2/ferragens/buscar?q=9999XXXINEXISTENTE")
    assert r.status_code == 404


def test_buscar_sem_q_retorna_422():
    r = client.get("/api/v2/ferragens/buscar")
    assert r.status_code == 422


# ─── 3. GET /api/v2/ferragens/filtros ────────────────────────────────────────

def test_filtros_retorna_200():
    r = client.get("/api/v2/ferragens/filtros")
    assert r.status_code == 200


def test_filtros_campos():
    body = client.get("/api/v2/ferragens/filtros").json()
    assert "linhas" in body
    assert "categorias" in body
    assert "total_canonicals" in body
    assert "santa_marina_1000" in body["linhas"]
    assert "dobradica" in body["categorias"]


# ─── 4. GET /api/v2/ferragens/{cid} ──────────────────────────────────────────

def test_detalhe_canonical_200():
    r = client.get("/api/v2/ferragens/1101")
    assert r.status_code == 200
    body = r.json()
    assert body["canonical_id"] == "1101"
    assert "variantes" in body
    assert "aliases" in body


def test_detalhe_canonical_404():
    r = client.get("/api/v2/ferragens/9999INEXISTENTE")
    assert r.status_code == 404


# ─── 5. GET /api/v2/ferragens/{cid}/variantes ────────────────────────────────

def test_variantes_200():
    r = client.get("/api/v2/ferragens/1101/variantes")
    assert r.status_code == 200
    body = r.json()
    assert body["canonical_id"] == "1101"
    assert body["total_variantes"] == 2


def test_variantes_404_canonical_inexistente():
    r = client.get("/api/v2/ferragens/9999XXXX/variantes")
    assert r.status_code == 404


# ─── 6. GET /api/v2/ferragens/kits ───────────────────────────────────────────

def test_kits_200():
    r = client.get("/api/v2/ferragens/kits")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["kits"][0]["kit_id"] == "KIT_TEST_01"
    assert body["kits"][0]["total_componentes"] == 1


def test_kits_filtra_por_fabricante():
    body = client.get("/api/v2/ferragens/kits?fabricante_origem=GLP").json()
    assert body["total"] == 1

    body_vazio = client.get("/api/v2/ferragens/kits?fabricante_origem=INEXISTENTE").json()
    assert body_vazio["total"] == 0


def test_detalhe_kit_200():
    r = client.get("/api/v2/ferragens/kits/KIT_TEST_01")
    assert r.status_code == 200
    body = r.json()
    assert body["kit_id"] == "KIT_TEST_01"
    assert len(body["componentes"]) == 1
    assert body["componentes"][0]["canonical_id"] == "1101"


def test_detalhe_kit_404():
    r = client.get("/api/v2/ferragens/kits/KIT_INEXISTENTE")
    assert r.status_code == 404


# ─── 7. GET /api/v2/ferragens/regras ─────────────────────────────────────────

def test_regras_200():
    r = client.get("/api/v2/ferragens/regras")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["regras"][0]["regra_id"] == "NBR_folga_movel_fixo"
    assert body["regras"][0]["valor_numerico"] == 3.0


def test_regras_filtra_por_categoria():
    body = client.get("/api/v2/ferragens/regras?categoria=folga_nbr7199").json()
    assert body["total"] == 1

    body_vazio = client.get("/api/v2/ferragens/regras?categoria=INEXISTENTE").json()
    assert body_vazio["total"] == 0


# ─── 8. v1 intacto ───────────────────────────────────────────────────────────

def test_v1_ferragens_ainda_funciona():
    r = client.get("/api/v1/canonical/ferragens")
    assert r.status_code == 200
    body = r.json()
    assert "ferragens" in body


def test_v1_materiais_ainda_funciona():
    r = client.get("/api/v1/canonical/materiais")
    assert r.status_code == 200


# ─── 9. recorte_canonico ─────────────────────────────────────────────────────

def test_detalhe_retorna_recorte_quando_preenchido():
    body = client.get("/api/v2/ferragens/1101").json()
    assert body["recorte_largura_mm"] == 27.0
    assert body["recorte_altura_mm"] == 110.0


def test_detalhe_retorna_recorte_null_quando_ausente():
    body = client.get("/api/v2/ferragens/1101R").json()
    assert body["recorte_largura_mm"] is None
    assert body["recorte_altura_mm"] is None


def test_buscar_retorna_recorte_quando_preenchido():
    body = client.get("/api/v2/ferragens/buscar?q=1101").json()
    assert body["recorte_largura_mm"] == 27.0
    assert body["recorte_altura_mm"] == 110.0
