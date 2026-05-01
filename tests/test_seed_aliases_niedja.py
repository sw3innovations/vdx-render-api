"""Testes para scripts/seed_aliases_niedja.py."""
from __future__ import annotations

import os
os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.constitution import _m010_schema_v2
from scripts.seed_aliases_niedja import (
    _ALIASES,
    run_seed,
)

_TRUNCAMENTO_PAIRS = [
    ("114", "1114"), ("302", "1302"), ("306", "1306"),
    ("310", "1310"), ("209", "1209"), ("320", "1320"),
    ("326", "1326"), ("329", "1329"), ("335", "1335"),
    ("510", "1510"), ("520", "1520"),
]
_ALL_TARGETS = {cid for _, cid, *_ in _ALIASES}


def _make_db(pre_canonicals: list[str] | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _m010_schema_v2(conn)
    conn.commit()
    for cid in (pre_canonicals or []):
        conn.execute(
            "INSERT OR IGNORE INTO canonicas "
            "(canonical_id, linha, categoria, nome_apresentacao) "
            "VALUES (?, 'santa_marina_1000', 'dobradica', ?)",
            (cid, f"Ferragem {cid}"),
        )
    conn.commit()
    return conn


# ─── 1. dry-run não escreve ──────────────────────────────────────────────────

def test_dry_run_writes_nothing():
    conn = _make_db()
    result = run_seed(conn, dry_run=True)
    assert conn.execute("SELECT COUNT(*) FROM canonicas").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM aliases_canonicos").fetchone()[0] == 0
    assert result.canonical_inserted == 1   # 1101R
    assert result.aliases_inserted == 13    # 11 truncamentos + 126D + gv
    assert result.pendentes_inserted == 2


# ─── 2. 11 truncamentos inseridos ───────────────────────────────────────────

def test_truncamentos_inseridos():
    # Pré-carrega todos os canonical_ids-alvo dos truncamentos
    targets = [cid for _, cid in _TRUNCAMENTO_PAIRS]
    conn = _make_db(pre_canonicals=targets)
    run_seed(conn, dry_run=False)

    rows = {r["alias"]: r["canonical_id"]
            for r in conn.execute(
                "SELECT alias, canonical_id FROM aliases_canonicos WHERE tipo='truncamento'"
            )}
    for alias, expected_cid in _TRUNCAMENTO_PAIRS:
        assert alias in rows, f"Alias '{alias}' não inserido"
        assert rows[alias] == expected_cid


# ─── 3. 126D como variant_id → 1126 ─────────────────────────────────────────

def test_126d_variant_alias():
    conn = _make_db(pre_canonicals=["1126"])
    run_seed(conn, dry_run=False)
    row = conn.execute(
        "SELECT canonical_id, tipo FROM aliases_canonicos WHERE alias='126D'"
    ).fetchone()
    assert row is not None
    assert row["canonical_id"] == "1126"
    assert row["tipo"] == "variant_id"


# ─── 4. gv → 1101R como apelido_comercial ───────────────────────────────────

def test_gv_alias_apelido():
    conn = _make_db()
    run_seed(conn, dry_run=False)
    # 1101R é criado pelo seed, então gv deve ser inserido
    row = conn.execute(
        "SELECT canonical_id, tipo FROM aliases_canonicos WHERE alias='gv'"
    ).fetchone()
    assert row is not None
    assert row["canonical_id"] == "1101R"
    assert row["tipo"] == "apelido_comercial"


# ─── 5. canonical 1101R criado com confidence=baixo ─────────────────────────

def test_1101r_canonical_attrs():
    conn = _make_db()
    run_seed(conn, dry_run=False)
    row = conn.execute(
        "SELECT linha, categoria, confidence FROM canonicas WHERE canonical_id='1101R'"
    ).fetchone()
    assert row is not None
    assert row["linha"] == "santa_marina_1000"
    assert row["categoria"] == "dobradica"
    assert row["confidence"] == "baixo"


# ─── 6. alias com canonical ausente → skip com warning (sem erro) ────────────

def test_alias_skipped_if_canonical_missing():
    # DB vazio: nenhum canonical pré-carregado
    conn = _make_db()
    result = run_seed(conn, dry_run=False)
    # 1101R é criado, então alias 'gv' é inserido
    # mas os 12 aliases de truncamentos/variant são todos skipped
    assert result.errors == []
    assert len(result.aliases_missing_canonical) > 0
    # Só o gv alias vai para 1101R (criado neste mesmo run)
    n_aliases = conn.execute("SELECT COUNT(*) FROM aliases_canonicos").fetchone()[0]
    assert n_aliases == 1  # só o gv→1101R


# ─── 7. jumbo + 1101R em pendentes_validacao_humana ─────────────────────────

def test_pendentes_jumbo_e_1101r():
    conn = _make_db()
    result = run_seed(conn, dry_run=False)
    assert result.pendentes_inserted == 2
    rows = conn.execute(
        "SELECT descricao FROM pendentes_validacao_humana"
    ).fetchall()
    descricoes = "\n".join(r[0] for r in rows)
    assert "jumbo" in descricoes.lower()
    assert "1101R" in descricoes


# ─── 8. idempotência ─────────────────────────────────────────────────────────

def test_idempotent():
    targets = [cid for _, cid in _TRUNCAMENTO_PAIRS] + ["1126"]
    conn = _make_db(pre_canonicals=targets)
    r1 = run_seed(conn, dry_run=False)
    r2 = run_seed(conn, dry_run=False)
    assert r2.canonical_inserted == 0
    assert r2.canonical_skipped == 1
    assert r2.aliases_inserted == 0
    assert r2.aliases_skipped == 13


# ─── 9. todos os aliases têm fonte='vendedora_niedja' ────────────────────────

def test_aliases_fonte_niedja():
    targets = [cid for _, cid in _TRUNCAMENTO_PAIRS] + ["1126"]
    conn = _make_db(pre_canonicals=targets)
    run_seed(conn, dry_run=False)
    n_other = conn.execute(
        "SELECT COUNT(*) FROM aliases_canonicos WHERE fonte != 'vendedora_niedja'"
    ).fetchone()[0]
    assert n_other == 0
