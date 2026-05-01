#!/usr/bin/env python3
"""
seed_aliases_niedja.py — popula aliases da vendedora Niedja no schema v2.

Fonte: confronto_vendedora_catalogos.md (22 fotos analisadas em 2026-05-01).

Popula:
  - `aliases_canonicos`         → 11 truncamentos + 1 variant_id (126D) + 1 apelido (gv)
  - `canonicas`                 → 1 novo: 1101R (dobradiça reforçada, confidence=baixo)
  - `pendentes_validacao_humana`→ 2 pendentes: jumbo (não id.), 1101R (confirmar)

Padrão de truncamento: código_vendedora = canonical_id − 1000 (para 1xxx).
Exceções (já 4 dígitos, sem alias): 1101, 1103, 1203, 3530.

Modo padrão: dry-run. Com --run: aplica.
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

DEFAULT_DB = Path(__file__).parent.parent / "data" / "constitution.db"

# ─── Dados da vendedora Niedja ────────────────────────────────────────────────

# (alias, canonical_id, tipo, obs)
_ALIASES: list[tuple[str, str, str, str | None]] = [
    # 11 truncamentos confirmados em ≥2 fontes independentes
    ("114",  "1114", "truncamento", "Vendedora omite '1' inicial (padrão sistemático)"),
    ("302",  "1302", "truncamento", None),
    ("306",  "1306", "truncamento", None),
    ("310",  "1310", "truncamento", None),
    ("209",  "1209", "truncamento", None),
    ("320",  "1320", "truncamento", None),
    ("326",  "1326", "truncamento", None),
    ("329",  "1329", "truncamento", None),
    ("335",  "1335", "truncamento", None),
    ("510",  "1510", "truncamento", None),
    ("520",  "1520", "truncamento", None),
    # 1 variant_id alias
    ("126D", "1126", "variant_id",
     "126D é variante 1126D dentro do canonical 1126 (não um truncamento simples). "
     "Glasspeças 2017 lista explicitamente: '1126, 126D, 126C, 126DC e 1126QC' na mesma família."),
    # 1 apelido comercial (gv → 1101R)
    ("gv",   "1101R", "apelido_comercial",
     "Foto gv.jpeg: dobradiça zamac/zamac reforçada, ~100-120mm, 3 castelinhos no topo, "
     "orifício em C, furo circular. Carimbo '3520' é número de lote GMS, não código de produto. "
     "Vendedora descreve como 'tipo a 114, para vidros maiores e mais pesados'."),
]

# Novo canonical (baixa confiança — aguarda confirmação física)
_CANONICAL_1101R = {
    "canonical_id":    "1101R",
    "linha":           "santa_marina_1000",
    "categoria":       "dobradica",
    "subcategoria":    "reforçada",
    "nome_apresentacao": "Dobradiça Superior Reforçada",
    "confidence":      "baixo",
    "fontes_pdf":      "glasspecas_2022 p.8-9 (hipótese visual)",
    "obs": (
        "Identificação a ~55% de confiança a partir da foto gv.jpeg da vendedora Niedja. "
        "Peça tem 3 furos (castelinhos) no topo, corpo com recorte em C, furo circular inferior, "
        "carimbo '3520' (número de lote GMS, não código). Pendente: confirmação com catálogo físico "
        "ou com a própria vendedora."
    ),
}

_PENDENTES = [
    {
        "descricao": "jumbo.jpeg — ferragem não identificada em nenhum dos 5 catálogos pesquisados",
        "contexto": (
            '{"arquivo": "jumbo.jpeg", "hipoteses": ['
            '"apelido informal para 1101/1103 tamanho extra-large", '
            '"ferragem de marca própria não catalogada", '
            '"sistema de box com dobradiça jumbo (ex: box 8mm folha grande)"], '
            '"acao": "perguntar à vendedora Niedja: código exato ou apelido informal?"}'
        ),
        "fonte": "confronto_vendedora_catalogos.md",
    },
    {
        "descricao": "1101R — confirmar identificação visual da foto gv.jpeg com catálogo físico ou com vendedora",
        "contexto": (
            '{"arquivo": "gv.jpeg", "canonical_id_hipotese": "1101R", "confidence": 0.55, '
            '"nota_3520": "carimbo \'3520\' na peça é número de lote GMS (Rodízio Excêntrico), '
            'não código da própria ferragem", '
            '"acao": "mostrar foto à vendedora Niedja + confirmar código exato"}'
        ),
        "fonte": "confronto_vendedora_catalogos.md",
    },
]


# ─── ETL ──────────────────────────────────────────────────────────────────────

@dataclass
class AliasResult:
    canonical_inserted: int = 0
    canonical_skipped: int = 0
    aliases_inserted: int = 0
    aliases_skipped: int = 0
    pendentes_inserted: int = 0
    aliases_missing_canonical: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def run_seed(conn: sqlite3.Connection, dry_run: bool = True) -> AliasResult:
    result = AliasResult()

    existing = {r[0] for r in conn.execute("SELECT canonical_id FROM canonicas")}

    # ── 1. Canonical 1101R ───────────────────────────────────────────────────
    c = _CANONICAL_1101R
    cid = c["canonical_id"]
    log.info("CANONICAL  %s  confidence=%s", cid, c["confidence"])

    if dry_run:
        result.canonical_inserted += 1
    else:
        try:
            cur = conn.execute(
                """INSERT OR IGNORE INTO canonicas
                   (canonical_id, linha, categoria, subcategoria,
                    nome_apresentacao, confidence, fontes_pdf, obs)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (cid, c["linha"], c["categoria"], c.get("subcategoria"),
                 c["nome_apresentacao"], c["confidence"],
                 c.get("fontes_pdf"), c.get("obs")),
            )
            if cur.rowcount:
                result.canonical_inserted += 1
                existing.add(cid)
            else:
                result.canonical_skipped += 1
        except Exception as e:
            result.errors.append(f"canonical {cid}: {e}")

    # ── 2. Aliases ───────────────────────────────────────────────────────────
    for (alias, canonical_id, tipo, obs) in _ALIASES:
        # Verifica se o canonical-alvo existe
        if canonical_id not in existing and not dry_run:
            log.warning(
                "ALIAS SKIP  %s → %s — canonical não existe no DB ainda "
                "(rodar ETL v2 antes)",
                alias, canonical_id,
            )
            result.aliases_missing_canonical.append(f"{alias}→{canonical_id}")
            continue

        log.info("ALIAS  %-6s → %-6s  [%s]", alias, canonical_id, tipo)

        if dry_run:
            result.aliases_inserted += 1
            continue

        try:
            cur = conn.execute(
                """INSERT OR IGNORE INTO aliases_canonicos
                   (canonical_id, alias, tipo, fonte, confidence)
                   VALUES (?, ?, ?, 'vendedora_niedja', 'alto')""",
                (canonical_id, alias, tipo),
            )
            if cur.rowcount:
                result.aliases_inserted += 1
            else:
                result.aliases_skipped += 1
        except Exception as e:
            result.errors.append(f"alias {alias}→{canonical_id}: {e}")

    # ── 3. Pendentes ─────────────────────────────────────────────────────────
    log.info("PENDENTE  jumbo + 1101R aguardam confirmação humana")
    if dry_run:
        result.pendentes_inserted = len(_PENDENTES)
    else:
        for p in _PENDENTES:
            try:
                conn.execute(
                    """INSERT INTO pendentes_validacao_humana
                       (descricao, contexto, fonte)
                       VALUES (?, ?, ?)""",
                    (p["descricao"], p["contexto"], p["fonte"]),
                )
                result.pendentes_inserted += 1
            except Exception as e:
                result.errors.append(f"pendente: {e}")
        conn.commit()

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()

    dry_run = not args.run
    db_path = Path(args.db)

    if not db_path.exists():
        log.error("DB não encontrado: %s", db_path)
        raise SystemExit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    log.info("=== Seed aliases Niedja — %s ===",
             "DRY-RUN" if dry_run else "APLICANDO")

    result = run_seed(conn, dry_run=dry_run)
    conn.close()

    log.info(
        "canonical +%d skip=%d | aliases +%d skip=%d missing=%d | "
        "pendentes=%d | erros=%d",
        result.canonical_inserted, result.canonical_skipped,
        result.aliases_inserted, result.aliases_skipped,
        len(result.aliases_missing_canonical),
        result.pendentes_inserted,
        len(result.errors),
    )
    if result.aliases_missing_canonical:
        log.warning("Aliases com canonical ausente: %s",
                    result.aliases_missing_canonical)


if __name__ == "__main__":
    main()
