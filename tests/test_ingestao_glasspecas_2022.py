"""Testes para scripts/ingestao_glasspecas_2022.py."""
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
from scripts.ingestao_glasspecas_2022 import (
    IngestaoResult,
    _canon,
    run_ingestao,
)


# ─── helpers ────────────────────────────────────────────────────────────────

def _make_db(pre_canonicals: list[str] | None = None) -> sqlite3.Connection:
    """DB in-memory com schema v2. Pré-carrega canonical_ids se informados."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _m010_schema_v2(conn)
    conn.commit()

    for cid in (pre_canonicals or []):
        conn.execute(
            "INSERT OR IGNORE INTO canonicas "
            "(canonical_id, linha, categoria, nome_apresentacao) "
            "VALUES (?, 'santa_marina_1000', 'suporte', ?)",
            (cid, f"Ferragem {cid}"),
        )
    conn.commit()
    return conn


# ─── 1. _canon() normalizador ────────────────────────────────────────────────

def test_canon_strips_suffix():
    assert _canon("1201SG") == "1201"
    assert _canon("1520MAG") == "1520"
    assert _canon("1629JG") == "1629"
    assert _canon("1003AG") == "1003"
    assert _canon("3530G") == "3530"
    assert _canon("1101PGAG") == "1101"


# ─── 2. dry-run não escreve ──────────────────────────────────────────────────

def test_dry_run_writes_nothing():
    conn = _make_db()
    result = run_ingestao(conn, dry_run=True)
    assert conn.execute("SELECT COUNT(*) FROM canonicas").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM regras_globais").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM kits_canonicos").fetchone()[0] == 0
    # Mas contabiliza o que faria
    assert result.canonicas_inserted == 4
    assert result.variantes_inserted == 14
    assert result.regras_inserted == 5
    assert result.kits_inserted == 18


# ─── 3. 4 novos canonicals inseridos ────────────────────────────────────────

def test_quatro_canonicals_inseridos():
    conn = _make_db()
    result = run_ingestao(conn, dry_run=False)
    assert result.canonicas_inserted == 4
    assert result.errors == []
    cids = {r[0] for r in conn.execute("SELECT canonical_id FROM canonicas")}
    assert {"1126", "1128", "1320", "1326"}.issubset(cids)


# ─── 4. variantes dos 4 novos canonicals ────────────────────────────────────

def test_variantes_novos_canonicals():
    conn = _make_db()
    run_ingestao(conn, dry_run=False)
    total = conn.execute(
        "SELECT COUNT(*) FROM variantes_canonicas"
    ).fetchone()[0]
    assert total == 14  # 9 variants 1126 + 3 variants 1128 + 1320G + 1326G

    count_1126 = conn.execute(
        "SELECT COUNT(*) FROM variantes_canonicas WHERE canonical_id='1126'"
    ).fetchone()[0]
    assert count_1126 == 9  # B, M, MC, C, D, DC, DCR, QC, 1126 base


# ─── 5. regras NBR inseridas ─────────────────────────────────────────────────

def test_regras_nbr_inseridas():
    conn = _make_db()
    run_ingestao(conn, dry_run=False)
    regras = {r["regra_id"]: r["valor_numerico"]
              for r in conn.execute("SELECT regra_id, valor_numerico FROM regras_globais")}
    assert regras["folga_movel_fixo"] == 3.0
    assert regras["folga_movel_movel"] == 4.0
    assert regras["folga_movel_piso"] == 8.0
    assert regras["folga_fixo_fixo"] == 1.0
    assert regras["folga_movel_alvenaria"] == 5.0


# ─── 6. kits inseridos ───────────────────────────────────────────────────────

def test_kits_inseridos():
    conn = _make_db()
    run_ingestao(conn, dry_run=False)
    n_kits = conn.execute("SELECT COUNT(*) FROM kits_canonicos").fetchone()[0]
    assert n_kits == 18


# ─── 7. kit componente com canonical ausente é pulado com warning ────────────

def test_componente_missing_canonical_skipped():
    # Pré-carrega só uma parte dos canonicals — simula DB parcial
    conn = _make_db(pre_canonicals=["1126", "1128", "1320", "1326",
                                    "1201", "1101", "1103", "1013", "1520", "1504"])
    result = run_ingestao(conn, dry_run=False)
    # Kits 17 e 18 têm componentes 3107, 3140, 3105, 3438, 3410, 3414 — ausentes
    assert len(result.componentes_missing_canonical) > 0
    # Erros NÃO devem ocorrer — apenas warnings
    assert result.errors == []


# ─── 8. idempotência ─────────────────────────────────────────────────────────

def test_idempotent():
    conn = _make_db()
    r1 = run_ingestao(conn, dry_run=False)
    r2 = run_ingestao(conn, dry_run=False)
    assert r2.canonicas_inserted == 0
    assert r2.canonicas_skipped == 4
    assert r2.regras_inserted == 0
    assert r2.regras_skipped == 5
    assert r2.kits_inserted == 0
    assert r2.kits_skipped == 18
    # kits_componentes: segunda rodada pula o insert do kit (skip), então
    # componentes nem chegam a ser tentados
    assert r2.componentes_inserted == 0


# ─── 9. 1126 tem linha=santa_marina_1000 e categoria=carrinho ────────────────

def test_1126_attrs():
    conn = _make_db()
    run_ingestao(conn, dry_run=False)
    row = conn.execute(
        "SELECT linha, categoria FROM canonicas WHERE canonical_id='1126'"
    ).fetchone()
    assert row["linha"] == "santa_marina_1000"
    assert row["categoria"] == "carrinho"


# ─── 10. kit componentes de kits completos são inseridos ────────────────────

def test_kit01_componentes_inseridos():
    # Kit 1: 1201, 1101, 1103, 1013, 1520, 1504
    needed = ["1201", "1101", "1103", "1013", "1520", "1504"]
    conn = _make_db(pre_canonicals=needed)
    run_ingestao(conn, dry_run=False)
    n = conn.execute(
        "SELECT COUNT(*) FROM kits_componentes WHERE kit_id='GLP_KIT01'"
    ).fetchone()[0]
    assert n == 6
