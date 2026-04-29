"""Importador idempotente de catálogos PDF de puxadores para constitution.db.

Uso via CLI: python -m app.cli.import_catalogo --catalog-dir ~/Downloads
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.core.constitution import _get_conn

log = logging.getLogger(__name__)

_CATALOG_FILES = [
    "extraido_al_vision.json",
    "extraido_glassvetro_vision.json",
    "extraido_bellnox.json",
    "extraido_tec_vidro.json",
    "extraido_catalogo_vidro.json",
]

_CATALOG_FABRICANTES = {
    "AL":            "Puxadores AL",
    "GLASSVETRO":    "Glassvetro",
    "BELLNOX":       "Bellnox",
    "TEC_VIDRO":     "Tec Vidro",
    "CATALOGO_VIDRO": "Catálogo Vidro",
}


def _normalizar_codigo(codigo: str | None) -> str | None:
    if not codigo:
        return None
    return re.sub(r"[\s\-/]", "", codigo).upper()


def _ensure_fabricante(conn, codigo: str) -> None:
    nome = _CATALOG_FABRICANTES.get(codigo, codigo)
    conn.execute(
        "INSERT OR IGNORE INTO catalogo_fabricantes (codigo, nome) VALUES (?, ?)",
        (codigo, nome),
    )


def _importar_produtos(conn, produtos: list[dict]) -> int:
    rows = []
    for p in produtos:
        dims = p.get("dimensoes_mm") or {}
        rows.append({
            "fabricante_id":      p.get("fabricante"),
            "codigo":             p.get("codigo"),
            "codigo_normalizado": _normalizar_codigo(p.get("codigo")),
            "nome":               p.get("nome"),
            "tipo_visual":        p.get("tipo_visual"),
            "comp_mm":            dims.get("comprimento"),
            "diametro_mm":        dims.get("diametro"),
            "largura_mm":         dims.get("largura"),
            "altura_mm":          dims.get("altura"),
            "profundidade_mm":    dims.get("profundidade"),
            "distancia_furos_mm": dims.get("distancia_entre_furos"),
            "material":           p.get("material"),
            "acabamento":         p.get("acabamento"),
            "observacoes":        p.get("observacoes"),
            "pagina_origem":      p.get("pagina_origem"),
        })

    conn.executemany(
        """INSERT OR IGNORE INTO catalogo_puxadores
           (fabricante_id, codigo, codigo_normalizado, nome, tipo_visual,
            comp_mm, diametro_mm, largura_mm, altura_mm, profundidade_mm,
            distancia_furos_mm, material, acabamento, observacoes, pagina_origem)
           VALUES
           (:fabricante_id, :codigo, :codigo_normalizado, :nome, :tipo_visual,
            :comp_mm, :diametro_mm, :largura_mm, :altura_mm, :profundidade_mm,
            :distancia_furos_mm, :material, :acabamento, :observacoes, :pagina_origem)""",
        rows,
    )
    return len(rows)


def importar_catalogo_arquivo(catalog_path: str | Path) -> dict[str, int]:
    """Importa um único arquivo de catálogo JSON. Idempotente (truncate-reload por fabricante)."""
    catalog_path = Path(catalog_path)
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    produtos = data.get("produtos", [])

    conn = _get_conn()
    fabricantes_vistos: set[str] = set()
    for p in produtos:
        fab = p.get("fabricante")
        if fab and fab not in fabricantes_vistos:
            _ensure_fabricante(conn, fab)
            fabricantes_vistos.add(fab)

    # Remove registros anteriores de cada fabricante antes de reinserir
    for fab in fabricantes_vistos:
        conn.execute("DELETE FROM catalogo_puxadores WHERE fabricante_id=?", (fab,))

    inserted = _importar_produtos(conn, produtos)
    conn.commit()
    conn.close()
    return {"arquivo": catalog_path.name, "produtos": len(produtos), "inseridos": inserted}


def importar_catalogos(catalog_dir: str | Path) -> dict[str, Any]:
    """Importa todos os arquivos de catálogo do diretório. Idempotente."""
    catalog_dir = Path(catalog_dir)
    total = 0
    arquivos: list[dict] = []

    for fname in _CATALOG_FILES:
        fpath = catalog_dir / fname
        if not fpath.exists():
            log.warning("Catálogo não encontrado: %s", fpath)
            continue
        stats = importar_catalogo_arquivo(fpath)
        arquivos.append(stats)
        total += stats["produtos"]
        log.info("Catálogo importado: %s", stats)

    return {"total_produtos": total, "arquivos": arquivos}
