"""Lookup de dimensões de puxadores no constitution.db com cache LRU."""
from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "constitution.db"


@lru_cache(maxsize=256)
def buscar_dimensoes_puxador(codigo: str, fabricante_id: str | None = None) -> dict | None:
    """Retorna dimensoes_json do puxador ou None se não encontrado/sem dimensões."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        row = conn.execute(
            "SELECT dimensoes_json FROM ferragens"
            " WHERE codigo_normalizado = ? AND tipo = 'puxador'"
            " AND (fabricante_id = ? OR ? IS NULL)"
            " LIMIT 1",
            (codigo, fabricante_id, fabricante_id),
        ).fetchone()
        conn.close()
        if row and row[0]:
            return json.loads(row[0])
    except Exception:
        pass
    return None
