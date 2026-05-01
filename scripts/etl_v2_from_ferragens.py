#!/usr/bin/env python3
"""
etl_v2_from_ferragens.py — popula canonicas + variantes_canonicas a partir de ferragens.

Lê as 164 rows de `ferragens` (não de `equivalencias`) e grava:
  - INSERT OR IGNORE em `canonicas`            (1 row por canonical_id único)
  - INSERT OR IGNORE em `variantes_canonicas`  (1 row por row de ferragens, exceto lixo)

Junk ignorado: FUSE001, NEWCI001 (fixtures de teste, fabricante SM).

Modo padrão: dry-run (só loga, não escreve).
Com --run:    escreve no banco.
Com --report: grava etl_v2_relatorio.md junto ao script.

Uso:
    python scripts/etl_v2_from_ferragens.py          # dry-run
    python scripts/etl_v2_from_ferragens.py --run    # aplica
    python scripts/etl_v2_from_ferragens.py --run --report
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

DEFAULT_DB = Path(__file__).parent.parent / "data" / "constitution.db"
REPORT_PATH = Path(__file__).parent.parent / "etl_v2_relatorio.md"

# Junk de teste — nunca migrar
_JUNK_CODIGOS = frozenset({"FUSE001", "NEWCI001"})

# Prioridade de nome canônico: menor = mais normativo
_NAME_PRIORITY: dict[str, int] = {"SM": 0, "AL": 1, "HE": 2}

# Mapeamento tipo → (categoria, subcategoria)
_CATEGORIA_MAP: dict[str, tuple[str, Optional[str]]] = {
    "dobradica":            ("dobradica", None),
    "dobradica_box":        ("dobradica", "box"),
    "dobradica_batente":    ("dobradica", "batente"),
    "dobradica_basculante": ("dobradica", "basculante"),
    "dobradica_superior":   ("dobradica", "superior"),
    "dobradica_inferior":   ("dobradica", "inferior"),
    "pivot":                ("pivo", None),
    "pivo":                 ("pivo", None),
    "puxador":              ("puxador", None),
    "fechadura":            ("fechadura", None),
    "contra_fechadura":     ("contra_fechadura", None),
    "suporte":              ("suporte", None),
    "trinco":               ("trinco", None),
    "batedor":              ("batedor", None),
    "bico_papagaio":        ("bico_papagaio", None),
    "corrente":             ("corrente", None),
    "calota":               ("calota", None),
    "capuchinho":           ("capuchinho", None),
    "roldana":              ("roldana", None),
    "facao":                ("facao", None),
    "pino":                 ("pino", None),
    "botao_correcao":       ("botao_correcao", None),
}


def _normalize_canonical_id(codigo_normalizado: str) -> str:
    """'PUXADOR 115' → 'PUXADOR-115'; '1101' → '1101'."""
    return re.sub(r"\s+", "-", codigo_normalizado.strip().upper())


def _linha_from_code(canonical_id: str) -> str:
    if re.match(r"^1\d{3}$", canonical_id):
        return "santa_marina_1000"
    if re.match(r"^3\d{3}$", canonical_id):
        return "blindex_3000"
    return "outro"


def _categoria_from_tipo(tipo: Optional[str]) -> tuple[str, Optional[str]]:
    return _CATEGORIA_MAP.get(tipo or "", (tipo or "outro", None))


def _variant_id(fabricante_id: str, codigo: str) -> str:
    """Gera variant_id estável: 'SM_1101SG', 'HE_HE_1013A', 'HE_PUXADOR_400'."""
    slug = re.sub(r"\s+", "_", codigo.strip())
    return f"{fabricante_id}_{slug}"


# ─── Estruturas de resultado ──────────────────────────────────────────────────

@dataclass
class ETLResult:
    canonicas_inserted: int = 0
    canonicas_skipped: int = 0
    variantes_inserted: int = 0
    variantes_skipped: int = 0
    junk_skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    canonical_ids: list[str] = field(default_factory=list)


# ─── Leitura da origem ────────────────────────────────────────────────────────

def load_ferragens(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT codigo, codigo_normalizado, fabricante_id, nome, tipo,
                  dimensoes_json, cores_json, espessura_vidro,
                  pagina_catalogo, confianca, fonte
           FROM ferragens
           ORDER BY codigo_normalizado,
                    CASE fabricante_id WHEN 'SM' THEN 0 WHEN 'AL' THEN 1 ELSE 2 END,
                    codigo"""
    ).fetchall()
    return [dict(r) for r in rows]


# ─── Derivação do melhor nome por canonical_id ────────────────────────────────

def _best_name_per_canonical(
    rows: list[dict],
) -> dict[str, tuple[str, Optional[str]]]:
    """Retorna {canonical_id: (nome, tipo)} usando SM > AL > HE como prioridade."""
    best: dict[str, tuple[int, str, Optional[str]]] = {}
    for r in rows:
        cid = _normalize_canonical_id(r["codigo_normalizado"])
        fab = r["fabricante_id"]
        prio = _NAME_PRIORITY.get(fab, 99)
        if cid not in best or prio < best[cid][0]:
            best[cid] = (prio, r["nome"], r["tipo"])
    return {k: (v[1], v[2]) for k, v in best.items()}


# ─── ETL principal ────────────────────────────────────────────────────────────

def run_etl(
    conn: sqlite3.Connection,
    dry_run: bool = True,
) -> ETLResult:
    result = ETLResult()
    rows = load_ferragens(conn)

    # Separa junk
    valid_rows = []
    for r in rows:
        if r["codigo"] in _JUNK_CODIGOS:
            result.junk_skipped.append(r["codigo"])
            log.info("JUNK  skipping %s (%s)", r["codigo"], r["fabricante_id"])
        else:
            valid_rows.append(r)

    best_names = _best_name_per_canonical(valid_rows)

    # ── passo 1: canonicas ────────────────────────────────────────────────────
    seen_canonicals: set[str] = set()
    for cid, (nome, tipo) in sorted(best_names.items()):
        seen_canonicals.add(cid)
        categoria, subcategoria = _categoria_from_tipo(tipo)
        linha = _linha_from_code(cid)
        result.canonical_ids.append(cid)

        log.info(
            "CANONICAL %s  linha=%s  cat=%s  nome=%s",
            cid, linha, categoria, nome[:40],
        )

        if dry_run:
            result.canonicas_inserted += 1
            continue

        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO canonicas
                   (canonical_id, linha, categoria, subcategoria,
                    nome_apresentacao, confidence, fontes_pdf)
                   VALUES (?, ?, ?, ?, ?, 'alto', 'ferragens_origem')""",
                (cid, linha, categoria, subcategoria, nome),
            )
            if cursor.rowcount:
                result.canonicas_inserted += 1
            else:
                result.canonicas_skipped += 1
        except Exception as e:
            result.errors.append(f"canonical {cid}: {e}")
            log.error("ERROR canonical %s: %s", cid, e)

    # ── passo 2: variantes ────────────────────────────────────────────────────
    for r in valid_rows:
        cid = _normalize_canonical_id(r["codigo_normalizado"])
        vid = _variant_id(r["fabricante_id"], r["codigo"])
        dims_json = r.get("dimensoes_json")

        # Combina dimensoes_json + cores_json + espessura_vidro em dimensoes_variantes_json
        dim_extra: dict = {}
        if dims_json:
            try:
                dim_extra = json.loads(dims_json) or {}
            except (json.JSONDecodeError, TypeError):
                dim_extra = {}
        if r.get("cores_json"):
            try:
                dim_extra["cores"] = json.loads(r["cores_json"])
            except (json.JSONDecodeError, TypeError):
                pass
        if r.get("espessura_vidro"):
            dim_extra["espessura_vidro"] = r["espessura_vidro"]
        dimensoes_variantes_json = json.dumps(dim_extra, ensure_ascii=False) if dim_extra else None

        log.debug(
            "VARIANT %s  fab=%s  codigo=%s",
            vid, r["fabricante_id"], r["codigo"],
        )

        if dry_run:
            result.variantes_inserted += 1
            continue

        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO variantes_canonicas
                   (variant_id, canonical_id, fabricante_codigo,
                    codigo_original, nome_comercial,
                    dimensoes_variantes_json, fonte_pdf, pagina_pdf,
                    extraction_quality)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completo')""",
                (
                    vid,
                    cid,
                    r["fabricante_id"],
                    r["codigo"],
                    r["nome"],
                    dimensoes_variantes_json,
                    r.get("fonte"),
                    r.get("pagina_catalogo"),
                ),
            )
            if cursor.rowcount:
                result.variantes_inserted += 1
            else:
                result.variantes_skipped += 1
        except Exception as e:
            result.errors.append(f"variant {vid}: {e}")
            log.error("ERROR variant %s: %s", vid, e)

    if not dry_run:
        conn.commit()

    return result


# ─── Relatório Markdown ───────────────────────────────────────────────────────

def write_report(result: ETLResult, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "APLICADO"
    lines = [
        "# ETL v2 — Relatório de Ingestão",
        f"",
        f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Modo:** {mode}  ",
        f"**Fonte:** tabela `ferragens` → `canonicas` + `variantes_canonicas`",
        f"",
        "---",
        "",
        "## Resumo",
        "",
        "| Métrica | Valor |",
        "|---|---|",
        f"| Canonicas inseridas | {result.canonicas_inserted} |",
        f"| Canonicas já existiam (skip) | {result.canonicas_skipped} |",
        f"| Variantes inseridas | {result.variantes_inserted} |",
        f"| Variantes já existiam (skip) | {result.variantes_skipped} |",
        f"| Junk ignorado | {len(result.junk_skipped)} |",
        f"| Erros | {len(result.errors)} |",
        "",
        "---",
        "",
        "## Canonical IDs processados",
        "",
        "```",
    ]
    for cid in sorted(result.canonical_ids):
        lines.append(cid)
    lines += [
        "```",
        "",
        "---",
        "",
        "## Junk ignorado",
        "",
    ]
    for j in result.junk_skipped:
        lines.append(f"- `{j}`")

    if result.errors:
        lines += ["", "---", "", "## Erros", ""]
        for e in result.errors:
            lines.append(f"- {e}")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Relatório gravado em %s", REPORT_PATH)


# ─── Entrypoint ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Aplica (padrão: dry-run)")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Caminho para constitution.db")
    parser.add_argument("--report", action="store_true", help="Grava etl_v2_relatorio.md")
    args = parser.parse_args()

    dry_run = not args.run
    db_path = Path(args.db)

    if not db_path.exists():
        log.error("DB não encontrado: %s", db_path)
        raise SystemExit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    mode_label = "DRY-RUN" if dry_run else "APLICANDO"
    log.info("=== ETL v2 — %s ===", mode_label)

    result = run_etl(conn, dry_run=dry_run)
    conn.close()

    log.info(
        "canonicas: +%d skip=%d | variantes: +%d skip=%d | junk=%d | erros=%d",
        result.canonicas_inserted,
        result.canonicas_skipped,
        result.variantes_inserted,
        result.variantes_skipped,
        len(result.junk_skipped),
        len(result.errors),
    )

    if args.report:
        write_report(result, dry_run=dry_run)


if __name__ == "__main__":
    main()
