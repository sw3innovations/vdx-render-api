"""Link staging records to canonical IDs."""
from __future__ import annotations
import sqlite3


def lookup_material_id(conn: sqlite3.Connection, codigo: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM materiais_canonicos WHERE codigo=?", (codigo,)
    ).fetchone()
    return row[0] if row else None


def lookup_acabamento_id(conn: sqlite3.Connection, codigo: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM acabamentos_canonicos WHERE codigo=?", (codigo,)
    ).fetchone()
    return row[0] if row else None


def lookup_tipologia_id(conn: sqlite3.Connection, nu_tip: int) -> int | None:
    row = conn.execute(
        "SELECT id FROM tipologias_canonicas WHERE nu_tip_dump=?", (nu_tip,)
    ).fetchone()
    return row[0] if row else None


def lookup_modelo_id(conn: sqlite3.Connection, nu_mod: int) -> int | None:
    row = conn.execute(
        "SELECT id FROM modelos_canonicos WHERE nu_mod_dump=?", (nu_mod,)
    ).fetchone()
    return row[0] if row else None


def upsert_alias_material(conn: sqlite3.Connection, material_id: int, alias: str, fonte: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO materiais_aliases (material_id, alias, fonte) VALUES (?,?,?)",
        (material_id, alias.lower(), fonte),
    )


def upsert_alias_acabamento(conn: sqlite3.Connection, acabamento_id: int, alias: str, fonte: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO acabamentos_aliases (acabamento_id, alias, fonte) VALUES (?,?,?)",
        (acabamento_id, alias.lower(), fonte),
    )
