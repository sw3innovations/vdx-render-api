"""
Constitution DB — base de conhecimento viva do plugin VDX.
SQLite local com WAL mode. Migra pra PostgreSQL quando escalar.
"""
import sqlite3
import json
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent.parent / "data" / "constitution.db"


def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = _get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS constitution_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nicho TEXT NOT NULL DEFAULT 'vidros',
        tipo TEXT NOT NULL,
        chave TEXT NOT NULL,
        dados TEXT NOT NULL,
        origem TEXT NOT NULL DEFAULT 'seed',
        confianca REAL NOT NULL DEFAULT 1.0,
        validado_por TEXT,
        versao TEXT NOT NULL DEFAULT '2026.03.20',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(nicho, tipo, chave)
    );

    CREATE TABLE IF NOT EXISTS constitution_aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nicho TEXT NOT NULL DEFAULT 'vidros',
        alias TEXT NOT NULL,
        canonical TEXT NOT NULL,
        tipo TEXT NOT NULL,
        origem TEXT NOT NULL DEFAULT 'seed',
        confianca REAL NOT NULL DEFAULT 1.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(nicho, alias, tipo)
    );

    CREATE INDEX IF NOT EXISTS idx_entries_chave ON constitution_entries(nicho, tipo, chave);
    CREATE INDEX IF NOT EXISTS idx_aliases_alias ON constitution_aliases(nicho, alias, tipo);

    CREATE TABLE IF NOT EXISTS constitution_validations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nicho TEXT NOT NULL DEFAULT 'vidros',
        entry_chave TEXT NOT NULL,
        tipo_validacao TEXT NOT NULL,
        resultado TEXT NOT NULL,
        correcoes TEXT,
        validado_por TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()


def buscar(chave: str, tipo: str = "tipologia", nicho: str = "vidros") -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT dados, confianca, origem FROM constitution_entries WHERE nicho=? AND tipo=? AND chave=?",
        (nicho, tipo, chave)
    ).fetchone()
    conn.close()
    if row:
        return {
            "dados": json.loads(row["dados"]),
            "confianca": row["confianca"],
            "origem": row["origem"]
        }
    return None


def registrar(chave: str, dados: dict, tipo: str = "tipologia",
              nicho: str = "vidros", origem: str = "claude_inferido",
              confianca: float = 0.7, validado_por: str = None):
    conn = _get_conn()
    conn.execute("""
        INSERT INTO constitution_entries (nicho, tipo, chave, dados, origem, confianca, validado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(nicho, tipo, chave) DO UPDATE SET
            dados=excluded.dados, origem=excluded.origem,
            confianca=excluded.confianca, validado_por=excluded.validado_por,
            updated_at=CURRENT_TIMESTAMP
    """, (nicho, tipo, chave, json.dumps(dados, ensure_ascii=False),
          origem, confianca, validado_por))
    conn.commit()
    conn.close()


def normalizar(nome: str, tipo: str = "tipologia", nicho: str = "vidros") -> str:
    """Resolve alias → canonical. Se não encontrar, retorna nome normalizado."""
    import unicodedata
    nome_norm = unicodedata.normalize('NFD', nome.lower().strip())
    nome_norm = ''.join(c for c in nome_norm if unicodedata.category(c) != 'Mn')
    nome_norm = nome_norm.replace(' ', '_').replace('-', '_')

    conn = _get_conn()
    row = conn.execute(
        "SELECT canonical FROM constitution_aliases WHERE nicho=? AND tipo=? AND alias=?",
        (nicho, tipo, nome_norm)
    ).fetchone()
    conn.close()
    if row:
        return row["canonical"]
    return nome_norm


def registrar_alias(alias: str, canonical: str, tipo: str = "tipologia",
                    nicho: str = "vidros", origem: str = "seed"):
    import unicodedata
    alias_norm = unicodedata.normalize('NFD', alias.lower().strip())
    alias_norm = ''.join(c for c in alias_norm if unicodedata.category(c) != 'Mn')
    alias_norm = alias_norm.replace(' ', '_').replace('-', '_')

    conn = _get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO constitution_aliases (nicho, alias, canonical, tipo, origem)
        VALUES (?, ?, ?, ?, ?)
    """, (nicho, alias_norm, canonical, tipo, origem))
    conn.commit()
    conn.close()


def marcar_validada(chave: str, tipo: str = "tipologia",
                    nicho: str = "vidros", confianca: float = 0.95):
    """Marca entry como validada, atualiza confiança."""
    conn = _get_conn()
    conn.execute(
        "UPDATE constitution_entries SET confianca=?, updated_at=CURRENT_TIMESTAMP "
        "WHERE nicho=? AND tipo=? AND chave=?",
        (confianca, nicho, tipo, chave))
    conn.commit()
    conn.close()


def registrar_validacao(chave: str, tipo_validacao: str, resultado: str,
                         correcoes: str = None,
                         validado_por: str = "claude_validator",
                         nicho: str = "vidros"):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO constitution_validations "
        "(nicho, entry_chave, tipo_validacao, resultado, correcoes, validado_por) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (nicho, chave, tipo_validacao, resultado, correcoes, validado_por))
    conn.commit()
    conn.close()


def foi_validada(chave: str, tipo: str = "tipologia", nicho: str = "vidros") -> bool:
    """Retorna True se a entry já tem confiança >= 0.95 (validada ou seed)."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT confianca FROM constitution_entries WHERE nicho=? AND tipo=? AND chave=?",
        (nicho, tipo, chave)).fetchone()
    conn.close()
    return bool(row and row["confianca"] >= 0.95)


def listar_entries(tipo: str = None, nicho: str = "vidros") -> list:
    conn = _get_conn()
    if tipo:
        rows = conn.execute(
            "SELECT chave, confianca, origem FROM constitution_entries WHERE nicho=? AND tipo=?",
            (nicho, tipo)).fetchall()
    else:
        rows = conn.execute(
            "SELECT tipo, chave, confianca, origem FROM constitution_entries WHERE nicho=?",
            (nicho,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
