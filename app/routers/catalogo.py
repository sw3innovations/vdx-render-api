"""
Router do catálogo público — expõe ferragens e kits do Constitution DB.
Sem autenticação: consumido diretamente pela UI do configurador.
"""
import json
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/catalogo", tags=["catalogo"])

_DB_PATH = Path("data/constitution.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _parse_json_field(value: Optional[str]) -> object:
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _ferragem_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "codigo": row["codigo"],
        "codigo_normalizado": row["codigo_normalizado"],
        "nome": row["nome"],
        "tipo": row["tipo"],
        "fabricante_id": row["fabricante_id"],
        "material": row["material"],
        "dimensoes": _parse_json_field(row["dimensoes_json"]),
        "espessura_vidro": row["espessura_vidro"],
        "cores": _parse_json_field(row["cores_json"]),
        "pagina_catalogo": row["pagina_catalogo"],
        "confianca": row["confianca"],
    }


def _kit_row_to_dict(row: sqlite3.Row, componentes: list[dict]) -> dict:
    return {
        "id": row["id"],
        "numero": row["numero"],
        "nome": row["nome"],
        "fabricante_id": row["fabricante_id"],
        "linha": row["linha"],
        "max_vao": _parse_json_field(row["max_vao_json"]),
        "acabamentos": _parse_json_field(row["acabamentos_json"]),
        "pagina_catalogo": row["pagina_catalogo"],
        "componentes": componentes,
    }


def _tipologia_keywords(tipologia: str) -> list[str]:
    """Extrai palavras-chave da chave de tipologia para match nos nomes de kits."""
    return [w for w in tipologia.lower().replace("_", " ").split() if len(w) > 2]


def _kit_match_tipologia(kit_nome: str, keywords: list[str]) -> bool:
    nome = kit_nome.lower()
    matches = sum(1 for kw in keywords if kw in nome)
    # 1-2 keywords: qualquer match; 3+ keywords: pelo menos 2 devem casar
    threshold = 1 if len(keywords) <= 2 else 2
    return matches >= threshold


def _fetch_componentes(cur: sqlite3.Cursor, kit_id: int) -> list[dict]:
    cur.execute(
        "SELECT ferragem_codigo, quantidade, posicao, nome FROM kit_componentes WHERE kit_id = ?",
        (kit_id,),
    )
    return [
        {
            "ferragem_codigo": r["ferragem_codigo"],
            "quantidade": r["quantidade"],
            "posicao": r["posicao"],
            "nome": r["nome"],
        }
        for r in cur.fetchall()
    ]


# ─── Ferragens ────────────────────────────────────────────────────────────────

@router.get("/ferragens")
def listar_ferragens(
    tipo: Optional[str] = None,
    fabricante: Optional[str] = None,
):
    """Lista ferragens do catálogo com filtros opcionais por tipo e fabricante."""
    with _conn() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM ferragens WHERE 1=1"
        params: list = []
        if tipo:
            query += " AND LOWER(tipo) = LOWER(?)"
            params.append(tipo)
        if fabricante:
            query += " AND LOWER(fabricante_id) = LOWER(?)"
            params.append(fabricante)
        query += " ORDER BY fabricante_id, tipo, nome"
        cur.execute(query, params)
        rows = cur.fetchall()
    return [_ferragem_row_to_dict(r) for r in rows]


@router.get("/ferragens/{tipo}")
def listar_ferragens_por_tipo(tipo: str):
    """Lista ferragens de um tipo específico (puxador, fechadura, dobradica, etc.)."""
    resultado = listar_ferragens(tipo=tipo)
    if not resultado:
        raise HTTPException(status_code=404, detail=f"Nenhuma ferragem do tipo '{tipo}' encontrada")
    return resultado


# ─── Kits ─────────────────────────────────────────────────────────────────────

@router.get("/kits")
def listar_kits(tipologia: Optional[str] = None):
    """Lista kits de ferragens. Filtro opcional por tipologia (match por palavras-chave)."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM kits ORDER BY fabricante_id, numero")
        rows = cur.fetchall()
        result = []
        keywords = _tipologia_keywords(tipologia) if tipologia else []
        for row in rows:
            if keywords and not _kit_match_tipologia(row["nome"], keywords):
                continue
            componentes = _fetch_componentes(cur, row["id"])
            result.append(_kit_row_to_dict(row, componentes))
    return result


@router.get("/kits/{tipologia}")
def listar_kits_por_tipologia(tipologia: str):
    """Lista kits aplicáveis a uma tipologia específica (ex: porta_pivotante_simples)."""
    resultado = listar_kits(tipologia=tipologia)
    if not resultado:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum kit encontrado para tipologia '{tipologia}'",
        )
    return resultado
