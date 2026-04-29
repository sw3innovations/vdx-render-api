"""Importador idempotente dos dados do dump VDX para o constitution.db.

Uso via CLI: python -m app.cli.import_dump --dump-dir /tmp/vdx_dump_v2/extracao
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.core.constitution import _get_conn

log = logging.getLogger(__name__)

_DUMP_FILES = {
    "tipologias":       "tipologias_tipos.json",
    "geometria_modelo": "geometria_por_modelo.json",
    "geometria_pecas":  "geometria_pecas.json",
    "var_altura":       "variaveis_altura.json",
    "var_largura":      "variaveis_largura.json",
    "categorias":       "categorias.json",
}


# ── loaders ──────────────────────────────────────────────────────────────────

def _load(dump_dir: Path, filename: str) -> Any:
    path = dump_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ── importers ─────────────────────────────────────────────────────────────────

def _importar_tipologias(conn, registros: list[dict]) -> int:
    conn.executemany(
        """INSERT OR REPLACE INTO dump_tipologias
           (nu_tip, ds_tmd, id_ativo, sacada)
           VALUES (:NU_TMD, :DS_TMD, :ID_ATIVO, :SACADA)""",
        registros,
    )
    return len(registros)


def _importar_modelos(conn, modelos_dict: dict) -> int:
    rows = [
        {
            "nu_mod":      int(k),
            "ds_mod":      v["DS_MOD"],
            "nu_tip":      v.get("NU_TMD"),
            "div_largura": v.get("DIV_LARGURA"),
            "div_altura":  v.get("DIV_ALTURA"),
        }
        for k, v in modelos_dict.items()
    ]
    conn.executemany(
        """INSERT OR REPLACE INTO dump_modelos
           (nu_mod, ds_mod, nu_tip, div_largura, div_altura)
           VALUES (:nu_mod, :ds_mod, :nu_tip, :div_largura, :div_altura)""",
        rows,
    )
    return len(rows)


def _importar_geometria_pecas(conn, registros: list[dict]) -> int:
    rows = [
        {
            "nu_dmd":          r.get("NU_DMD"),
            "nu_mod":          r["NU_MOD"],
            "nu_peca":         r["NU_PECA"],
            "eixo_x_alt":      r.get("EIXO_X_ALT"),
            "eixo_x_lar":      r.get("EIXO_X_LARG"),
            "eixo_y_alt":      r.get("EIXO_Y_ALT"),
            "eixo_y_lar":      r.get("EIXO_Y_LARG"),
            "ds_formula_alt":  r.get("DS_FORMULA_ALT"),
            "ds_formula_lar":  r.get("DS_FORMULA_LARG"),
            "ds_tipo":         r.get("DS_TIPO"),
            "ds_peca":         r.get("DS_PECA"),
            "ds_descricao":    r.get("DS_DESCRICAO"),
        }
        for r in registros
    ]
    conn.executemany(
        """INSERT OR REPLACE INTO dump_geometria_pecas
           (nu_dmd, nu_mod, nu_peca,
            eixo_x_alt, eixo_x_lar, eixo_y_alt, eixo_y_lar,
            ds_formula_alt, ds_formula_lar,
            ds_tipo, ds_peca, ds_descricao)
           VALUES (:nu_dmd, :nu_mod, :nu_peca,
                   :eixo_x_alt, :eixo_x_lar, :eixo_y_alt, :eixo_y_lar,
                   :ds_formula_alt, :ds_formula_lar,
                   :ds_tipo, :ds_peca, :ds_descricao)""",
        rows,
    )
    return len(rows)


def _importar_variaveis_altura(conn, registros: list[dict]) -> int:
    conn.executemany(
        """INSERT OR REPLACE INTO dump_variaveis_altura
           (nu_mda, nu_mod, ds_altura, var_altura, altura_padrao)
           VALUES (:NU_MDA, :NU_MOD, :DS_ALTURA, :VAR_ALTURA, :ALTURA_PADRAO)""",
        registros,
    )
    return len(registros)


def _importar_variaveis_largura(conn, registros: list[dict]) -> int:
    conn.executemany(
        """INSERT OR REPLACE INTO dump_variaveis_largura
           (nu_mdl, nu_mod, ds_largura, var_largura, largura_padrao)
           VALUES (:NU_MDL, :NU_MOD, :DS_LARGURA, :VAR_LARGURA, :LARGURA_PADRAO)""",
        registros,
    )
    return len(registros)


def _importar_categorias(conn, registros: list[dict]) -> int:
    rows = [{"nu_cat": r["NU_CAT"], "ds_cat": r["DS_CAT"], "id_ativo": r.get("ID_ATIVO")} for r in registros]
    conn.executemany(
        """INSERT OR REPLACE INTO dump_categorias_ferragens
           (nu_cat, ds_cat, id_ativo)
           VALUES (:nu_cat, :ds_cat, :id_ativo)""",
        rows,
    )
    return len(rows)


# ── public API ────────────────────────────────────────────────────────────────

def importar_dump(dump_dir: str | Path) -> dict[str, int]:
    """Importa todos os arquivos do dump para constitution.db. Idempotente."""
    dump_dir = Path(dump_dir)
    conn = _get_conn()
    stats: dict[str, int] = {}

    tip_data = _load(dump_dir, _DUMP_FILES["tipologias"])
    stats["tipologias"] = _importar_tipologias(conn, tip_data["registros"])

    mod_data = _load(dump_dir, _DUMP_FILES["geometria_modelo"])
    stats["modelos"] = _importar_modelos(conn, mod_data)

    geo_data = _load(dump_dir, _DUMP_FILES["geometria_pecas"])
    stats["geometria_pecas"] = _importar_geometria_pecas(conn, geo_data["registros"])

    va_data = _load(dump_dir, _DUMP_FILES["var_altura"])
    stats["variaveis_altura"] = _importar_variaveis_altura(conn, va_data["registros"])

    vl_data = _load(dump_dir, _DUMP_FILES["var_largura"])
    stats["variaveis_largura"] = _importar_variaveis_largura(conn, vl_data["registros"])

    cat_data = _load(dump_dir, _DUMP_FILES["categorias"])
    stats["categorias"] = _importar_categorias(conn, cat_data["registros"])

    conn.commit()
    conn.close()

    log.info("Dump importado: %s", stats)
    return stats
