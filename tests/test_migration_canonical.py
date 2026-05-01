"""Testes para scripts/migrate_constitution_canonical.py."""
from __future__ import annotations

import os
os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

import json
import sqlite3
import tempfile
from pathlib import Path
import sys

import pytest

# Importa funções core do migration script
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.migrate_constitution_canonical import (
    _has_conflict,
    _linha_from_code,
    _pct_diff,
    apply_to_db,
    load_equivalencias,
    load_ferragens,
    load_recortes,
    migrate,
    write_json,
    write_report,
)


# ─── fixtures ────────────────────────────────────────────────────────────────

def _make_db(tmp_path: Path) -> Path:
    """Cria um SQLite mínimo com os mesmos schemas das tabelas migradas."""
    db_path = tmp_path / "test_constitution.db"
    conn = sqlite3.connect(str(db_path))
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
            pagina_catalogo INTEGER
        );
        CREATE TABLE equivalencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_normalizado TEXT NOT NULL,
            fabricante_id TEXT NOT NULL,
            codigo_fabricante TEXT NOT NULL
        );
        CREATE TABLE recortes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ferragem_codigo TEXT NOT NULL,
            fabricante_id TEXT NOT NULL,
            tipo TEXT,
            comprimento_mm REAL,
            largura_mm REAL,
            furo_diametro_mm REAL,
            raio_mm REAL
        );
        CREATE TABLE ferragens_canonicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_normalizado TEXT NOT NULL,
            tipo TEXT,
            subtipo TEXT,
            nome_apresentacao TEXT NOT NULL,
            material_id INTEGER,
            acabamento_id INTEGER,
            fabricante_codigo TEXT,
            comprimento_mm REAL,
            diametro_mm REAL,
            largura_mm REAL,
            altura_mm REAL,
            profundidade_mm REAL,
            distancia_furos_mm REAL,
            fontes_json TEXT,
            observacoes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(codigo_normalizado, fabricante_codigo)
        );
    """)
    conn.execute("INSERT INTO fabricantes VALUES ('SM','Glasspeças','SM')")
    conn.execute("INSERT INTO fabricantes VALUES ('HE','HELA','HE')")
    conn.execute("INSERT INTO fabricantes VALUES ('AL','AL Indústria','AL')")
    conn.commit()
    conn.close()
    return db_path


def _insert_ferragem(db_path: Path, codigo: str, cn: str, fab: str, nome: str, tipo: str = "dobradica"):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO ferragens (codigo, codigo_normalizado, fabricante_id, nome, tipo) VALUES (?,?,?,?,?)",
        (codigo, cn, fab, nome, tipo),
    )
    conn.commit()
    conn.close()


def _insert_recorte(db_path: Path, code: str, fab: str, comp: float, larg: float):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO recortes (ferragem_codigo, fabricante_id, tipo, comprimento_mm, largura_mm) VALUES (?,?,?,?,?)",
        (code, fab, "onda", comp, larg),
    )
    conn.commit()
    conn.close()


# ─── helpers ────────────────────────────────────────────────────────────────

def test_linha_santa_marina():
    assert _linha_from_code("1101") == "santa_marina_1000"
    assert _linha_from_code("1001") == "santa_marina_1000"


def test_linha_blindex():
    assert _linha_from_code("3210") == "blindex_3000"
    assert _linha_from_code("3530") == "blindex_3000"


def test_linha_outro():
    assert _linha_from_code("9999") == "outro"
    assert _linha_from_code("ABCD") == "outro"


def test_pct_diff_zero_same():
    assert _pct_diff(100.0, 100.0) == 0.0


def test_pct_diff_none_returns_zero():
    assert _pct_diff(None, 100.0) == 0.0
    assert _pct_diff(100.0, None) == 0.0


def test_has_conflict_no_conflict():
    a = {"comprimento_mm": 110.0, "largura_mm": 25.0}
    b = {"comprimento_mm": 110.0, "largura_mm": 25.0}
    assert not _has_conflict(a, b)


def test_has_conflict_detects_divergence():
    a = {"comprimento_mm": 110.0, "largura_mm": 25.0}
    b = {"comprimento_mm": 120.0, "largura_mm": 25.0}  # ~9% diff
    assert _has_conflict(a, b)


def test_has_conflict_within_threshold():
    a = {"comprimento_mm": 110.0}
    b = {"comprimento_mm": 112.0}  # ~1.8% diff — within 5%
    assert not _has_conflict(a, b)


# ─── TAREFA 1a — caminho feliz (múltiplas variantes) ─────────────────────────

def test_migrate_happy_path_multiple_variants(tmp_path):
    db = _make_db(tmp_path)
    _insert_ferragem(db, "1101SG", "1101", "SM", "Dobradiça Superior SM")
    _insert_ferragem(db, "HE 1101A", "1101", "HE", "Dobradiça Superior HE")
    _insert_ferragem(db, "1101A", "1101", "AL", "Dobradiça Superior AL")

    result = migrate(db)
    assert result["stats"]["total_canonicos"] == 1
    assert result["stats"]["total_orfas"] == 0
    c = result["canonicos"][0]
    assert c["canonical_id"] == "1101"
    assert c["linha"] == "santa_marina_1000"
    assert len(c["variantes"]) == 3
    fabs = {v["fabricante_id"] for v in c["variantes"]}
    assert fabs == {"SM", "HE", "AL"}


# ─── TAREFA 1b — conflito de dimensão detectado ──────────────────────────────

def test_migrate_conflict_detection(tmp_path):
    db = _make_db(tmp_path)
    _insert_ferragem(db, "1101SG", "1101", "SM", "Dobradiça Superior SM")
    _insert_ferragem(db, "HE 1101A", "1101", "HE", "Dobradiça Superior HE")
    # SM recorte: 110mm × 25mm
    _insert_recorte(db, "1101SG", "SM", 110.0, 25.0)
    # HE recorte: 125mm × 27mm (>5% diferente)
    _insert_recorte(db, "HE 1101A", "HE", 125.0, 27.0)

    result = migrate(db)
    assert result["stats"]["total_conflitos"] >= 1
    c = result["canonicos"][0]
    assert len(c["_conflitos"]) >= 1


# ─── TAREFA 1c — ferragem órfã (prefixo desconhecido) ────────────────────────

def test_migrate_orphan_detected(tmp_path):
    db = _make_db(tmp_path)
    _insert_ferragem(db, "PUXADOR 300", "PUXADOR 300", "AL", "Puxador 300mm")

    result = migrate(db)
    assert result["stats"]["total_orfas"] == 1
    assert result["orfas"][0]["codigo"] == "PUXADOR 300"
    assert result["stats"]["total_canonicos"] == 0


# ─── TAREFA 1d — variante única (um fabricante) ──────────────────────────────

def test_migrate_single_variant(tmp_path):
    db = _make_db(tmp_path)
    _insert_ferragem(db, "AL 1402", "1402", "AL", "Articulador para basculante AL")

    result = migrate(db)
    assert result["stats"]["total_canonicos"] == 1
    c = result["canonicos"][0]
    assert c["canonical_id"] == "1402"
    assert len(c["variantes"]) == 1
    assert c["variantes"][0]["fabricante_id"] == "AL"


# ─── TAREFA 1e — múltiplas variantes com sub-sufixos ─────────────────────────

def test_migrate_multiple_subsuffix_variants(tmp_path):
    db = _make_db(tmp_path)
    _insert_ferragem(db, "AL 1002", "1002", "AL", "Botão Simples")
    _insert_ferragem(db, "AL 1002A", "1002", "AL", "Botão Lâmina")
    _insert_ferragem(db, "AL 1002B", "1002", "AL", "Botão Lâmina com Calota")
    _insert_ferragem(db, "HE 1002A", "1002", "HE", "Botão HE")

    result = migrate(db)
    c = result["canonicos"][0]
    assert c["canonical_id"] == "1002"
    variant_ids = [v["variant_id"] for v in c["variantes"]]
    # Todos devem ser únicos
    assert len(set(variant_ids)) == len(variant_ids), f"variant_ids duplicados: {variant_ids}"
    assert len(c["variantes"]) == 4


# ─── TAREFA 1f — output JSON e relatório gerados corretamente ────────────────

def test_write_json_creates_file(tmp_path):
    db = _make_db(tmp_path)
    _insert_ferragem(db, "1101SG", "1101", "SM", "Dobradiça SM")
    result = migrate(db)
    out = tmp_path / "v2.json"
    write_json(result, out)
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["schema_version"] == "v2"
    assert len(data["ferragens_canonicas"]) == 1


def test_write_report_creates_file(tmp_path):
    db = _make_db(tmp_path)
    _insert_ferragem(db, "1101SG", "1101", "SM", "Dobradiça SM")
    result = migrate(db)
    out = tmp_path / "report.md"
    write_report(result, out)
    assert out.exists()
    content = out.read_text()
    assert "1101" in content
    assert "santa_marina_1000" in content


# ─── TAREFA 1g — apply insere em ferragens_canonicas ─────────────────────────

def test_apply_inserts_into_ferragens_canonicas(tmp_path):
    db = _make_db(tmp_path)
    _insert_ferragem(db, "1101SG", "1101", "SM", "Dobradiça SM")
    _insert_ferragem(db, "HE 1101A", "1101", "HE", "Dobradiça HE")

    result = migrate(db)
    n = apply_to_db(result, db)
    assert n == 2

    conn = sqlite3.connect(str(db))
    rows = conn.execute("SELECT codigo_normalizado, fabricante_codigo FROM ferragens_canonicas").fetchall()
    conn.close()
    assert len(rows) == 2
    assert {r[0] for r in rows} == {"1101"}
    assert {r[1] for r in rows} == {"SM", "HE"}


def test_apply_idempotent(tmp_path):
    """Rodar --apply duas vezes não duplica registros."""
    db = _make_db(tmp_path)
    _insert_ferragem(db, "1101SG", "1101", "SM", "Dobradiça SM")

    result = migrate(db)
    n1 = apply_to_db(result, db)
    n2 = apply_to_db(result, db)
    assert n1 == 1
    assert n2 == 0  # INSERT OR IGNORE — nenhum novo

    conn = sqlite3.connect(str(db))
    count = conn.execute("SELECT COUNT(*) FROM ferragens_canonicas").fetchone()[0]
    conn.close()
    assert count == 1
