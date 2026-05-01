"""Testes para scripts/etl_v2_from_ferragens.py."""
from __future__ import annotations

import os
os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.etl_v2_from_ferragens import (
    ETLResult,
    _categoria_from_tipo,
    _linha_from_code,
    _normalize_canonical_id,
    _variant_id,
    run_etl,
)
from app.core.constitution import _m010_schema_v2


# ─── helpers ────────────────────────────────────────────────────────────────

def _make_db(ferragens: list[dict]) -> sqlite3.Connection:
    """Cria DB in-memory com schema v2 + dados de ferragens fornecidos."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE fabricantes (
            id TEXT PRIMARY KEY, nome TEXT NOT NULL, prefixo TEXT NOT NULL
        );
        CREATE TABLE ferragens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            codigo_normalizado TEXT NOT NULL,
            fabricante_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT,
            dimensoes_json TEXT,
            espessura_vidro TEXT,
            cores_json TEXT,
            pagina_catalogo INTEGER,
            confianca REAL DEFAULT 0.9,
            fonte TEXT,
            UNIQUE(codigo, fabricante_id)
        );
    """)

    _m010_schema_v2(conn)
    conn.commit()

    for f in ferragens:
        conn.execute(
            "INSERT OR IGNORE INTO ferragens "
            "(codigo, codigo_normalizado, fabricante_id, nome, tipo, "
            "dimensoes_json, espessura_vidro, cores_json, pagina_catalogo, fonte) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f["codigo"], f["codigo_normalizado"], f["fabricante_id"],
                f["nome"], f.get("tipo"), f.get("dimensoes_json"),
                f.get("espessura_vidro"), f.get("cores_json"),
                f.get("pagina_catalogo"), f.get("fonte"),
            ),
        )
    conn.commit()
    return conn


_SAMPLE_FERRAGENS = [
    # 1101 — 3 fabricantes (SM melhor nome)
    {"codigo": "1101SG",   "codigo_normalizado": "1101", "fabricante_id": "SM", "nome": "Dobradiça Superior 1101", "tipo": "dobradica"},
    {"codigo": "HE 1101",  "codigo_normalizado": "1101", "fabricante_id": "HE", "nome": "Dobradiça HE 1101",       "tipo": "dobradica"},
    {"codigo": "HE 1101A", "codigo_normalizado": "1101", "fabricante_id": "HE", "nome": "Dobradiça HE 1101A",      "tipo": "dobradica"},
    {"codigo": "AL 1101",  "codigo_normalizado": "1101", "fabricante_id": "AL", "nome": "Dobradiça AL 1101",       "tipo": "dobradica"},
    # 1302 — só AL
    {"codigo": "AL 1302",  "codigo_normalizado": "1302", "fabricante_id": "AL", "nome": "Suporte de Canto 1302",   "tipo": "suporte"},
    # PUXADOR 115 — HE
    {"codigo": "PUXADOR 115", "codigo_normalizado": "PUXADOR 115", "fabricante_id": "HE", "nome": "Puxador Bola 115mm", "tipo": "puxador"},
    # Junk
    {"codigo": "FUSE001",  "codigo_normalizado": "FUSE001",  "fabricante_id": "SM", "nome": "Junk A", "tipo": None},
    {"codigo": "NEWCI001", "codigo_normalizado": "NEWCI001", "fabricante_id": "SM", "nome": "Junk B", "tipo": None},
]


# ─── 1. funções utilitárias ──────────────────────────────────────────────────

def test_normalize_canonical_id():
    assert _normalize_canonical_id("1101") == "1101"
    assert _normalize_canonical_id("PUXADOR 115") == "PUXADOR-115"
    assert _normalize_canonical_id("PUXADOR  400") == "PUXADOR-400"


def test_linha_from_code():
    assert _linha_from_code("1101") == "santa_marina_1000"
    assert _linha_from_code("3530") == "blindex_3000"
    assert _linha_from_code("PUXADOR-115") == "outro"


def test_categoria_from_tipo():
    assert _categoria_from_tipo("dobradica_box") == ("dobradica", "box")
    assert _categoria_from_tipo("pivot") == ("pivo", None)
    assert _categoria_from_tipo("suporte") == ("suporte", None)
    assert _categoria_from_tipo(None) == ("outro", None)


def test_variant_id():
    assert _variant_id("SM", "1101SG") == "SM_1101SG"
    assert _variant_id("HE", "HE 1013A") == "HE_HE_1013A"
    assert _variant_id("HE", "PUXADOR 400") == "HE_PUXADOR_400"


# ─── 2. dry-run não escreve no banco ────────────────────────────────────────

def test_dry_run_writes_nothing():
    conn = _make_db(_SAMPLE_FERRAGENS)
    result = run_etl(conn, dry_run=True)
    assert conn.execute("SELECT COUNT(*) FROM canonicas").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM variantes_canonicas").fetchone()[0] == 0
    # Mas contabiliza o que faria
    assert result.canonicas_inserted > 0
    assert result.variantes_inserted > 0
    conn.close()


# ─── 3. run popula canonicas com contagem correta ───────────────────────────

def test_run_creates_expected_canonicas():
    conn = _make_db(_SAMPLE_FERRAGENS)
    result = run_etl(conn, dry_run=False)
    # 3 canonical_ids distintos: 1101, 1302, PUXADOR-115
    assert conn.execute("SELECT COUNT(*) FROM canonicas").fetchone()[0] == 3
    assert result.canonicas_inserted == 3
    assert result.junk_skipped == ["FUSE001", "NEWCI001"]
    conn.close()


# ─── 4. sub-variantes não são colapsadas ────────────────────────────────────

def test_subvariantes_not_collapsed():
    """HE 1101 e HE 1101A devem gerar 2 variantes distintas, não 1."""
    conn = _make_db(_SAMPLE_FERRAGENS)
    run_etl(conn, dry_run=False)
    # 1101 tem: SM(1), HE(2), AL(1) = 4 variantes; 1302 tem AL(1); PUXADOR-115 tem HE(1)
    total_variantes = conn.execute(
        "SELECT COUNT(*) FROM variantes_canonicas"
    ).fetchone()[0]
    assert total_variantes == 6  # 4 + 1 + 1

    he_variants_1101 = conn.execute(
        "SELECT COUNT(*) FROM variantes_canonicas "
        "WHERE canonical_id='1101' AND fabricante_codigo='HE'"
    ).fetchone()[0]
    assert he_variants_1101 == 2, "HE 1101 e HE 1101A devem ser variantes separadas"
    conn.close()


# ─── 5. nome canônico usa SM como prioridade ─────────────────────────────────

def test_canonical_nome_uses_sm_priority():
    conn = _make_db(_SAMPLE_FERRAGENS)
    run_etl(conn, dry_run=False)
    row = conn.execute(
        "SELECT nome_apresentacao FROM canonicas WHERE canonical_id='1101'"
    ).fetchone()
    assert row is not None
    assert row[0] == "Dobradiça Superior 1101"  # nome do SM, não HE nem AL
    conn.close()


# ─── 6. idempotência: rodar 2x não duplica rows ──────────────────────────────

def test_idempotent():
    conn = _make_db(_SAMPLE_FERRAGENS)
    r1 = run_etl(conn, dry_run=False)
    r2 = run_etl(conn, dry_run=False)
    assert r2.canonicas_inserted == 0
    assert r2.canonicas_skipped == 3
    assert r2.variantes_inserted == 0
    assert r2.variantes_skipped == 6
    assert conn.execute("SELECT COUNT(*) FROM canonicas").fetchone()[0] == 3
    conn.close()


# ─── 7. PUXADOR-115 recebe linha='outro' e categoria='puxador' ───────────────

def test_puxador_canonical_attrs():
    conn = _make_db(_SAMPLE_FERRAGENS)
    run_etl(conn, dry_run=False)
    row = conn.execute(
        "SELECT linha, categoria FROM canonicas WHERE canonical_id='PUXADOR-115'"
    ).fetchone()
    assert row is not None
    assert row["linha"] == "outro"
    assert row["categoria"] == "puxador"
    conn.close()


# ─── 8. dimensoes_variantes_json preserva dados originais ───────────────────

def test_dimensoes_preserved():
    ferragens = [
        {
            "codigo": "HE 1101",
            "codigo_normalizado": "1101",
            "fabricante_id": "HE",
            "nome": "Dobradiça HE 1101",
            "tipo": "dobradica",
            "dimensoes_json": '{"comprimento": 45.0, "largura": 18.0}',
            "espessura_vidro": "8-10mm",
        }
    ]
    conn = _make_db(ferragens)
    run_etl(conn, dry_run=False)
    row = conn.execute(
        "SELECT dimensoes_variantes_json FROM variantes_canonicas WHERE variant_id='HE_HE_1101'"
    ).fetchone()
    assert row is not None
    data = json.loads(row[0])
    assert data["comprimento"] == 45.0
    assert data["espessura_vidro"] == "8-10mm"
    conn.close()
