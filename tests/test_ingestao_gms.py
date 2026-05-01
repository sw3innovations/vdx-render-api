"""Testes para scripts/ingestao_gms_blindex.py."""
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
from scripts.ingestao_gms_blindex import (
    _GMS_ITEMS,
    _JA_EM_CANONICAS,
    _VARIANTES_EXTRAS_GMS,
    _linha_from_id,
    run_ingestao,
)


def _make_db(pre_canonicals: list[str] | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _m010_schema_v2(conn)
    conn.commit()
    for cid in (pre_canonicals or []):
        conn.execute(
            "INSERT OR IGNORE INTO canonicas "
            "(canonical_id, linha, categoria, nome_apresentacao) "
            "VALUES (?, 'blindex_3000', 'suporte', ?)",
            (cid, f"Ferragem {cid}"),
        )
    conn.commit()
    return conn


# ─── 1. _linha_from_id ───────────────────────────────────────────────────────

def test_linha_blindex_3xxx():
    assert _linha_from_id("3001") == "blindex_3000"
    assert _linha_from_id("3530") == "blindex_3000"
    assert _linha_from_id("4718") == "blindex_3000"


def test_linha_outro():
    assert _linha_from_id("BLX72") == "outro"


# ─── 2. dry-run não escreve ──────────────────────────────────────────────────

def test_dry_run_writes_nothing():
    conn = _make_db()
    result = run_ingestao(conn, dry_run=True)
    assert conn.execute("SELECT COUNT(*) FROM canonicas").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM variantes_canonicas").fetchone()[0] == 0
    assert result.canonicas_inserted == 119
    assert result.variantes_inserted == 127  # 119 novos + 8 extras existentes
    assert result.pendentes_inserted == 2


# ─── 3. 119 novos canonicals inseridos ──────────────────────────────────────

def test_novos_canonicals_count():
    conn = _make_db()
    result = run_ingestao(conn, dry_run=False)
    assert result.canonicas_inserted == 119
    assert result.errors == []
    n = conn.execute("SELECT COUNT(*) FROM canonicas").fetchone()[0]
    assert n == 119


# ─── 4. variantes GMS — 119 novas + 8 extras para existentes ────────────────

def test_variantes_gms_count():
    # Pré-carrega os 8 já existentes para que variantes_extras sejam inseridas
    conn = _make_db(pre_canonicals=list(_JA_EM_CANONICAS))
    run_ingestao(conn, dry_run=False)
    total = conn.execute(
        "SELECT COUNT(*) FROM variantes_canonicas"
    ).fetchone()[0]
    assert total == 127

    # Todas variantes têm fabricante_codigo='GMS'
    n_gms = conn.execute(
        "SELECT COUNT(*) FROM variantes_canonicas WHERE fabricante_codigo='GMS'"
    ).fetchone()[0]
    assert n_gms == 127


# ─── 5. canonical 3520 é Rodízio (não dobradiça) ────────────────────────────

def test_3520_is_rodizio():
    conn = _make_db()
    run_ingestao(conn, dry_run=False)
    row = conn.execute(
        "SELECT categoria, nome_apresentacao FROM canonicas WHERE canonical_id='3520'"
    ).fetchone()
    assert row is not None
    assert row["categoria"] == "roldana"
    assert "Rodízio" in row["nome_apresentacao"]


# ─── 6. 3105, 3107, 3140, 3438, 3410, 3414 inseridos (kits 17/18) ───────────

def test_kit1718_deps_inserted():
    conn = _make_db()
    run_ingestao(conn, dry_run=False)
    for cid in ("3105", "3107", "3140", "3438", "3410", "3414"):
        row = conn.execute(
            "SELECT canonical_id FROM canonicas WHERE canonical_id=?", (cid,)
        ).fetchone()
        assert row is not None, f"canonical {cid} não foi inserido"


# ─── 7. LGL e TQ inseridos como pendentes ───────────────────────────────────

def test_lgl_tq_pendentes():
    conn = _make_db()
    result = run_ingestao(conn, dry_run=False)
    assert result.pendentes_inserted == 2
    rows = conn.execute(
        "SELECT descricao FROM pendentes_validacao_humana"
    ).fetchall()
    descricoes = [r[0] for r in rows]
    assert any("LGL" in d for d in descricoes)
    assert any("TQ" in d for d in descricoes)


# ─── 8. grupo 31 inclui dobradiças com linha blindex_3000 ───────────────────

def test_grupo31_linha():
    conn = _make_db()
    run_ingestao(conn, dry_run=False)
    row = conn.execute(
        "SELECT linha, categoria FROM canonicas WHERE canonical_id='3140'"
    ).fetchone()
    assert row["linha"] == "blindex_3000"
    assert row["categoria"] == "dobradica"


# ─── 9. idempotência ─────────────────────────────────────────────────────────

def test_idempotent():
    conn = _make_db(pre_canonicals=list(_JA_EM_CANONICAS))
    r1 = run_ingestao(conn, dry_run=False)
    r2 = run_ingestao(conn, dry_run=False)
    assert r2.canonicas_inserted == 0
    assert r2.canonicas_skipped == 119
    assert r2.variantes_inserted == 0
    assert r2.variantes_skipped == 127
