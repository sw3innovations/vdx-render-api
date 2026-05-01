"""Testes para a migração _m010_schema_v2 — 9 novas tabelas do schema v2."""
from __future__ import annotations

import os
os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

import sqlite3
import tempfile
from pathlib import Path

import pytest

from app.core.constitution import _m010_schema_v2


@pytest.fixture()
def v2_conn():
    """Conexão in-memory com apenas as tabelas que _m010 depende já criadas."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # m010 não tem FKs para tabelas anteriores — pode rodar standalone
    _m010_schema_v2(conn)
    conn.commit()
    yield conn
    conn.close()


# ── 1. Todas as 9 tabelas existem ────────────────────────────────────────────

_EXPECTED_TABLES = {
    "funcoes_canonicas",
    "canonicas",
    "aliases_canonicos",
    "variantes_canonicas",
    "alternativas_funcionais",
    "kits_canonicos",
    "kits_componentes",
    "regras_globais",
    "pendentes_validacao_humana",
}


def test_all_v2_tables_created(v2_conn):
    tables = {
        row[0]
        for row in v2_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert _EXPECTED_TABLES.issubset(tables), (
        f"Tabelas faltando: {_EXPECTED_TABLES - tables}"
    )


# ── 2. Insert + FK integridade (canonicas → funcoes_canonicas) ───────────────

def test_canonicas_insert_and_fk(v2_conn):
    v2_conn.execute(
        "INSERT INTO funcoes_canonicas (funcao_id, nome_descritivo, categoria_uso) "
        "VALUES ('dobradicao_superior', 'Dobradiça Superior', 'dobradicao')"
    )
    v2_conn.execute(
        "INSERT INTO canonicas "
        "(canonical_id, funcao_id, linha, categoria, nome_apresentacao) "
        "VALUES ('1101', 'dobradicao_superior', 'santa_marina_1000', 'dobradica', "
        "'Dobradiça Superior 1101')"
    )
    v2_conn.commit()
    row = v2_conn.execute(
        "SELECT canonical_id, linha FROM canonicas WHERE canonical_id='1101'"
    ).fetchone()
    assert row is not None
    assert row["linha"] == "santa_marina_1000"


# ── 3. aliases_canonicos — UNIQUE(alias, canonical_id) ───────────────────────

def test_alias_unique_constraint(v2_conn):
    v2_conn.execute(
        "INSERT INTO canonicas (canonical_id, linha, categoria, nome_apresentacao) "
        "VALUES ('1302', 'santa_marina_1000', 'suporte', 'Suporte 1302')"
    )
    v2_conn.execute(
        "INSERT INTO aliases_canonicos (canonical_id, alias, tipo) "
        "VALUES ('1302', '302', 'truncamento')"
    )
    v2_conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        v2_conn.execute(
            "INSERT INTO aliases_canonicos (canonical_id, alias, tipo) "
            "VALUES ('1302', '302', 'truncamento')"
        )
        v2_conn.commit()


# ── 4. variantes_canonicas — índices existem ─────────────────────────────────

def test_variantes_indices_exist(v2_conn):
    indices = {
        row[0]
        for row in v2_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }
    assert "idx_variante_canonical" in indices
    assert "idx_variante_fabricante" in indices
    assert "idx_alias_busca" in indices


# ── 5. regras_globais e pendentes inserem sem erro ───────────────────────────

def test_regras_and_pendentes_insert(v2_conn):
    v2_conn.execute(
        "INSERT INTO regras_globais (regra_id, categoria, descricao, valor_numerico, unidade, fonte) "
        "VALUES ('folga_inferior_box', 'folga_nbr', 'Folga inferior caixa de box', 10.0, 'mm', 'NBR 7199')"
    )
    v2_conn.execute(
        "INSERT INTO pendentes_validacao_humana (descricao, contexto, fonte) "
        "VALUES ('jumbo.jpeg — ferragem não identificada', "
        "'{\"arquivo\": \"jumbo.jpeg\"}', 'vendedora_niedja')"
    )
    v2_conn.commit()
    assert v2_conn.execute(
        "SELECT COUNT(*) FROM regras_globais"
    ).fetchone()[0] == 1
    assert v2_conn.execute(
        "SELECT COUNT(*) FROM pendentes_validacao_humana"
    ).fetchone()[0] == 1


# ── 6. migration é idempotente (rodar 2x não lança erro) ─────────────────────

def test_m010_idempotent():
    conn = sqlite3.connect(":memory:")
    _m010_schema_v2(conn)
    conn.commit()
    _m010_schema_v2(conn)  # segunda chamada não deve lançar
    conn.commit()
    conn.close()
