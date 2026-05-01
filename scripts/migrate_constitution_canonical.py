#!/usr/bin/env python3
"""
migrate_constitution_canonical.py — refatora Constitution DB para chave canônica Santa Marina.

Lê as tabelas legadas `ferragens` + `equivalencias` + `recortes` e gera:
  - constitution_db_v2.json     (schema canônico — NÃO sobrescreve constitution.db)
  - migration_report.md         (o que mudou, conflitos, órfãs)

Com --apply: também insere os dados migrados em ferragens_canonicas.

Uso:
    python scripts/migrate_constitution_canonical.py [--apply] [--db PATH]
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

DEFAULT_DB = Path(__file__).parent.parent / "data" / "constitution.db"
OUT_JSON = Path(__file__).parent.parent / "constitution_db_v2.json"
OUT_REPORT = Path(__file__).parent.parent / "migration_report.md"

# Prefixos conhecidos de fabricantes
_KNOWN_PREFIXES = {"SM", "HE", "AL"}

# Prioridade de fonte para recorte canônico (menor índice = mais normativo)
_SOURCE_PRIORITY = {"SM": 0, "HE": 1, "AL": 2}


def _get_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _linha_from_code(canonical_id: str) -> str:
    if re.match(r"^3\d{3}$", canonical_id):
        return "blindex_3000"
    if re.match(r"^1\d{3}$", canonical_id):
        return "santa_marina_1000"
    return "outro"


def _pct_diff(a: float | None, b: float | None) -> float:
    """Divergência percentual entre dois valores. Retorna 0.0 se algum for None."""
    if a is None or b is None:
        return 0.0
    if a == 0 and b == 0:
        return 0.0
    base = max(abs(a), abs(b))
    return abs(a - b) / base


def _has_conflict(recortes_a: dict, recortes_b: dict, threshold: float = 0.05) -> bool:
    """Retorna True se qualquer dimensão dimensional divergir mais que threshold."""
    dims = ["comprimento_mm", "largura_mm", "furo_diametro_mm", "raio_mm"]
    for dim in dims:
        va = recortes_a.get(dim)
        vb = recortes_b.get(dim)
        if va is not None and vb is not None:
            if _pct_diff(va, vb) > threshold:
                return True
    return False


def load_ferragens(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT codigo, codigo_normalizado, fabricante_id, nome, tipo, dimensoes_json "
        "FROM ferragens ORDER BY codigo_normalizado, fabricante_id"
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("dimensoes_json"):
            try:
                d["dimensoes"] = json.loads(d["dimensoes_json"])
            except Exception:
                d["dimensoes"] = {}
        else:
            d["dimensoes"] = {}
        result.append(d)
    return result


def load_recortes(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    """Retorna dict: codigo_ferragem → lista de recortes."""
    rows = conn.execute(
        "SELECT ferragem_codigo, fabricante_id, tipo, comprimento_mm, largura_mm, "
        "furo_diametro_mm, raio_mm FROM recortes"
    ).fetchall()
    result: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        result[r["ferragem_codigo"]].append(dict(r))
    return result


def load_equivalencias(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    """Retorna dict: codigo_normalizado → lista de equivalencias."""
    rows = conn.execute(
        "SELECT codigo_normalizado, fabricante_id, codigo_fabricante FROM equivalencias"
    ).fetchall()
    result: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        result[r["codigo_normalizado"]].append(dict(r))
    return result


def load_fabricantes(conn: sqlite3.Connection) -> dict[str, dict]:
    rows = conn.execute("SELECT id, nome, prefixo FROM fabricantes").fetchall()
    return {r["id"]: dict(r) for r in rows}


def _pick_canonical_recorte(
    canonical_id: str, variants: list[dict], recortes_map: dict[str, list[dict]]
) -> tuple[dict | None, list[str]]:
    """
    Escolhe o recorte canônico (fonte mais normativa = SM > HE > AL).
    Retorna (recorte_canonico, lista_de_conflitos).
    """
    # Coleta todos os recortes disponíveis por fabricante
    recortes_by_fab: dict[str, dict] = {}
    for v in variants:
        fab = v["fabricante_id"]
        # Busca recortes pelo codigo exato ou codigo_normalizado do fabricante
        for code in [v["codigo"], v.get("codigo_normalizado", "")]:
            if code in recortes_map:
                for r in recortes_map[code]:
                    recortes_by_fab.setdefault(fab, r)
                break

    if not recortes_by_fab:
        return None, []

    # Ordena por prioridade (SM=0, HE=1, AL=2, outros=99)
    def priority(fab: str) -> int:
        return _SOURCE_PRIORITY.get(fab, 99)

    sorted_fabs = sorted(recortes_by_fab.keys(), key=priority)
    canonical_fab = sorted_fabs[0]
    canonical_rec = recortes_by_fab[canonical_fab]

    # Detecta conflitos entre variantes
    conflicts: list[str] = []
    for fab, rec in recortes_by_fab.items():
        if fab == canonical_fab:
            continue
        if _has_conflict(canonical_rec, rec):
            conflicts.append(
                f"{fab} vs {canonical_fab}: comprimento={rec.get('comprimento_mm')} "
                f"vs {canonical_rec.get('comprimento_mm')}"
            )

    return canonical_rec, conflicts


def migrate(db_path: Path) -> dict[str, Any]:
    """
    Lê o estado atual do DB e constrói o schema canônico em memória.
    Retorna dict com: canonicos, orfas, conflitos, stats.
    """
    conn = _get_conn(db_path)
    ferragens = load_ferragens(conn)
    recortes_map = load_recortes(conn)
    equivalencias = load_equivalencias(conn)
    fabricantes = load_fabricantes(conn)
    conn.close()

    # Agrupa ferragens por codigo_normalizado
    groups: dict[str, list[dict]] = defaultdict(list)
    orfas: list[dict] = []

    for f in ferragens:
        cn = f.get("codigo_normalizado", "")
        if re.match(r"^\d{4}$", cn):
            groups[cn].append(f)
        else:
            orfas.append(f)
            log.warning("Órfã detectada: %s (codigo_normalizado='%s')", f["codigo"], cn)

    canonicos: list[dict] = []
    all_conflicts: list[dict] = []

    for canonical_id, variants in sorted(groups.items()):
        linha = _linha_from_code(canonical_id)

        # Determina categoria do tipo mais comum entre as variantes
        tipos = [v["tipo"] for v in variants if v.get("tipo")]
        categoria = max(set(tipos), key=tipos.count) if tipos else None

        # Monta recorte canônico
        rec_canonico, conflicts = _pick_canonical_recorte(canonical_id, variants, recortes_map)
        if conflicts:
            all_conflicts.extend([
                {"canonical_id": canonical_id, "detalhe": c} for c in conflicts
            ])

        recorte_canonico = None
        if rec_canonico:
            recorte_canonico = {
                "tipo": rec_canonico.get("tipo"),
                "comprimento_mm": rec_canonico.get("comprimento_mm"),
                "largura_mm": rec_canonico.get("largura_mm"),
                "furo_diametro_mm": rec_canonico.get("furo_diametro_mm"),
                "raio_mm": rec_canonico.get("raio_mm"),
                # STUB: furos[] e raios_canto[] precisam de dado geométrico adicional
                # não disponível nas tabelas atuais (somente escalares, sem x/y).
                "furos": None,
                "raios_canto": None,
                "fonte_fabricante": rec_canonico.get("fabricante_id"),
            }

        # Monta variantes
        variantes: list[dict] = []
        for v in variants:
            fab_id = v["fabricante_id"]
            fab_nome = fabricantes.get(fab_id, {}).get("nome", fab_id)
            fab_prefixo = fabricantes.get(fab_id, {}).get("prefixo", fab_id)

            # Recorte desta variante (para detectar dimensoes_variantes)
            rec_variante: dict = {}
            for code in [v["codigo"], v.get("codigo_normalizado", "")]:
                if code in recortes_map:
                    rec_variante = recortes_map[code][0]
                    break

            dimensoes_variantes: dict = {}
            if rec_variante and rec_canonico:
                for dim in ["comprimento_mm", "largura_mm", "furo_diametro_mm", "raio_mm"]:
                    if _pct_diff(rec_variante.get(dim), rec_canonico.get(dim)) > 0.01:
                        dimensoes_variantes[dim] = rec_variante.get(dim)

            # Build variant suffix from original code (e.g. "AL 1002A" → "A")
            raw_code = re.sub(r'\s+', '', v["codigo"])
            after_digits = re.sub(r'^[A-Z]*\d{4}', '', raw_code).strip("-_")
            variant_suffix = f"-{after_digits}" if after_digits else ""
            variant_id = f"{canonical_id}-{fab_prefixo}{variant_suffix}"

            variantes.append({
                "variant_id": variant_id,
                "fabricante": fab_nome,
                "fabricante_id": fab_id,
                "codigo_original": v["codigo"],
                "nome_comercial": v["nome"],
                "sufixo": fab_prefixo + variant_suffix,
                "dimensoes": v.get("dimensoes") or {},
                "dimensoes_variantes": dimensoes_variantes,
                "fonte_pdf": None,
                "pagina_pdf": v.get("pagina_catalogo"),
                "conflito_detectado": bool(
                    conflicts and any(fab_id in c for c in conflicts)
                ),
            })

        # Adiciona entradas da tabela equivalencias que não têm row em ferragens
        covered_fabs = {v["fabricante_id"] for v in variants}
        for eq in equivalencias.get(canonical_id, []):
            if eq["fabricante_id"] not in covered_fabs:
                fab_id = eq["fabricante_id"]
                fab_nome = fabricantes.get(fab_id, {}).get("nome", fab_id)
                fab_prefixo = fabricantes.get(fab_id, {}).get("prefixo", fab_id)
                variantes.append({
                    "variant_id": f"{canonical_id}-{fab_prefixo}",
                    "fabricante": fab_nome,
                    "fabricante_id": fab_id,
                    "codigo_original": eq["codigo_fabricante"],
                    "nome_comercial": None,
                    "sufixo": fab_prefixo,
                    "dimensoes": {},
                    "dimensoes_variantes": {},
                    "fonte_pdf": None,
                    "pagina_pdf": None,
                    "conflito_detectado": False,
                })

        canonicos.append({
            "canonical_id": canonical_id,
            "linha": linha,
            "categoria": categoria,
            "funcao_descricao": variants[0]["nome"] if variants else None,
            "recorte_canonico": recorte_canonico,
            "carga_max_kg_nbr16835": None,
            "ciclos_min_nbr16835": None,
            "variantes": variantes,
            "_conflitos": conflicts if conflicts else [],
        })

    return {
        "canonicos": canonicos,
        "orfas": orfas,
        "conflitos": all_conflicts,
        "stats": {
            "total_ferragens_legadas": len(ferragens),
            "total_canonicos": len(canonicos),
            "total_orfas": len(orfas),
            "total_conflitos": len(all_conflicts),
            "total_variantes": sum(len(c["variantes"]) for c in canonicos),
        },
    }


def write_json(result: dict[str, Any], out_path: Path) -> None:
    payload = {
        "schema_version": "v2",
        "gerado_por": "migrate_constitution_canonical.py",
        "ferragens_canonicas": result["canonicos"],
        "_orfas": result["orfas"],
        "_conflitos": result["conflitos"],
        "stats": result["stats"],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    log.info("JSON gerado: %s (%d bytes)", out_path, out_path.stat().st_size)


def write_report(result: dict[str, Any], out_path: Path) -> None:
    s = result["stats"]
    lines: list[str] = [
        "# Migration Report — Constitution DB v2",
        "",
        "## Stats",
        f"| Métrica | Valor |",
        f"|---|---|",
        f"| Ferragens legadas lidas | {s['total_ferragens_legadas']} |",
        f"| Canônicos gerados | {s['total_canonicos']} |",
        f"| Variantes totais | {s['total_variantes']} |",
        f"| Órfãs (sem prefixo conhecido) | {s['total_orfas']} |",
        f"| Conflitos de recorte detectados | {s['total_conflitos']} |",
        "",
        "## Campos stub (a preencher manualmente)",
        "- `recorte_canonico.furos[]` — fonte atual tem apenas `furo_diametro_mm` (escalar); "
        "array de furos com x/y requer dado geométrico adicional.",
        "- `recorte_canonico.raios_canto[]` — fonte atual tem apenas `raio_mm` (escalar); "
        "array por canto requer geometria adicional.",
        "- `carga_max_kg_nbr16835`, `ciclos_min_nbr16835` — não disponível no catálogo atual.",
        "- `fonte_pdf`, `pagina_pdf` das variantes — maioria `null`; preencher ao importar TQ/LGL.",
        "",
        "## Canônicos gerados",
        "",
    ]
    for c in result["canonicos"]:
        n_var = len(c["variantes"])
        fab_list = ", ".join(v["fabricante_id"] for v in c["variantes"])
        conf_marker = " ⚠️ CONFLITO" if c.get("_conflitos") else ""
        lines.append(
            f"- **{c['canonical_id']}** ({c['linha']}) · {n_var} variante(s): "
            f"{fab_list}{conf_marker}"
        )

    if result["conflitos"]:
        lines += [
            "",
            "## Conflitos detectados (recorte diverge > 5%)",
            "",
            "Estes canônicos precisam de revisão humana antes de consolidar recorte:",
            "",
        ]
        for cf in result["conflitos"]:
            lines.append(f"- `{cf['canonical_id']}` — {cf['detalhe']}")

    if result["orfas"]:
        lines += [
            "",
            "## Ferragens órfãs (sem prefixo conhecido — revisão manual necessária)",
            "",
        ]
        for o in result["orfas"]:
            lines.append(
                f"- `{o['codigo']}` (codigo_normalizado=`{o['codigo_normalizado']}`, "
                f"fab=`{o['fabricante_id']}`)"
            )
    else:
        lines += ["", "## Ferragens órfãs", "", "Nenhuma — todos os prefixos foram reconhecidos. ✅"]

    out_path.write_text("\n".join(lines) + "\n")
    log.info("Relatório gerado: %s", out_path)


def apply_to_db(result: dict[str, Any], db_path: Path) -> int:
    """
    Insere canônicos em ferragens_canonicas.
    Usa INSERT OR IGNORE — seguro executar múltiplas vezes.
    Retorna número de rows inseridas.
    """
    conn = _get_conn(db_path)
    inserted = 0
    for c in result["canonicos"]:
        for v in c["variantes"]:
            try:
                # Resolve material_id e acabamento_id como None (sem mapeamento automático)
                conn.execute(
                    """INSERT OR IGNORE INTO ferragens_canonicas
                       (codigo_normalizado, tipo, subtipo, nome_apresentacao,
                        fabricante_codigo, observacoes, fontes_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        c["canonical_id"],
                        c["categoria"],
                        None,
                        v["nome_comercial"] or c.get("funcao_descricao") or c["canonical_id"],
                        v["fabricante_id"],
                        "migrado de ferragens legadas via migrate_constitution_canonical.py",
                        json.dumps({"codigo_original": v["codigo_original"]}),
                    ),
                )
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    inserted += 1
            except Exception as e:
                log.warning("Falha ao inserir %s/%s: %s", c["canonical_id"], v["fabricante_id"], e)
    conn.commit()
    conn.close()
    log.info("Aplicado: %d rows inseridas em ferragens_canonicas", inserted)
    return inserted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Aplica migração no DB")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Caminho do SQLite")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    if not db_path.exists():
        log.error("DB não encontrado: %s", db_path)
        return 1

    log.info("Lendo Constitution DB em: %s", db_path)
    result = migrate(db_path)
    s = result["stats"]

    log.info(
        "Migração concluída: %d canônicos, %d variantes, %d órfãs, %d conflitos",
        s["total_canonicos"], s["total_variantes"], s["total_orfas"], s["total_conflitos"],
    )

    write_json(result, OUT_JSON)
    write_report(result, OUT_REPORT)

    if args.apply:
        n = apply_to_db(result, db_path)
        log.info("--apply: %d rows inseridas no DB", n)
    else:
        log.info("DRY-RUN: use --apply para escrever no DB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
