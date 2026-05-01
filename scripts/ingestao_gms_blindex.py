#!/usr/bin/env python3
"""
ingestao_gms_blindex.py — ingere dados do catálogo GMS-Blindex (47 pgs, /tmp/gms_blindex.pdf).

Popula:
  - `canonicas`            → ~120 novos canonical_ids (Grupos 30-38 + Linha Santa Marina)
  - `variantes_canonicas`  → 1 variante GMS por canonical (fabricante_codigo='GMS')
  - Para códigos já em canonicas: apenas adiciona variante GMS (INSERT OR IGNORE)
  - `pendentes_validacao_humana` → LGL e TQ (sem arquivos disponíveis)

Nota: o código '3520' (Rodízio Excêntrico para Porta de Correr) é um produto real GMS-Blindex.
O carimbo "3520" encontrado na foto gv.jpeg é número de lote, NÃO código de produto.

Modo padrão: dry-run. Com --run: aplica.

Uso:
    python scripts/ingestao_gms_blindex.py
    python scripts/ingestao_gms_blindex.py --run
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

# ─── Catálogo GMS-Blindex extraído de /tmp/gms_blindex.pdf ──────────────────
# Formato: (canonical_id, nome, categoria, subcategoria, pagina_pdf)
# Codes já em canonicas: apenas variante GMS é adicionada (canonical skip)

_GMS_ITEMS: list[tuple[str, str, str, str | None, int]] = [
    # ── Grupo 30 — SUPORTES (págs 3-6) ──────────────────────────────────────
    ("3001", "Suporte Duplo Vertical",                       "suporte", None,         3),
    ("3002", "Suporte Duplo Horizontal",                     "suporte", None,         3),
    ("3003", "Suporte Duplo Vertical com Capuchinho",        "suporte", None,         3),
    ("3004", "Suporte Duplo Central",                        "suporte", None,         3),
    ("3005", "Suporte Duplo Horizontal com Aba Reta",        "suporte", None,         3),
    ("3006", "Suporte Simples Vertical",                     "suporte", None,         3),
    ("3007", "Suporte Simples Vertical com Capuchinho",      "suporte", None,         3),
    ("3009", "Suporte Simples de Canto",                     "suporte", "canto",      3),
    ("3010", "Suporte Simples de Centro",                    "suporte", None,         4),
    ("3011", "Suporte de Canto Esquerdo com Aba Reta",       "suporte", "canto",      4),
    ("3012", "Suporte de Canto Direito com Aba Reta",        "suporte", "canto",      4),
    ("3013", "Suporte de Centro com Capuchinho",             "suporte", None,         4),
    ("3014", "Suporte Quadruplo",                            "suporte", None,         4),
    ("3016", "Suporte Triplo",                               "suporte", None,         4),
    ("3017", "Suporte Triplo com Aparador Reversível",       "suporte", None,         4),
    ("3018", "Suporte Alongado 25mm",                        "suporte", None,         4),
    ("3019", "Suporte Alongado 50mm",                        "suporte", None,         5),
    ("3020", "Suporte Triplo com Contra Trinco Direito",     "suporte", None,         5),
    ("3021", "Suporte Triplo com Contra Trinco Esquerdo",    "suporte", None,         5),
    ("3022", "Cantoneira com Núcleo",                        "suporte", "cantoneira", 5),
    ("3023", "Cantoneira sem Núcleo",                        "suporte", "cantoneira", 5),
    ("3025", "Cantoneira Quádruplo",                         "suporte", "cantoneira", 5),
    ("3027", "Suporte Contra Trinco Esquerdo (p/ 3413)",     "suporte", None,         5),
    ("3028", "Suporte Contra Trinco Direito (p/ 3412)",      "suporte", None,         5),
    ("3030", "Capuchinho de Lâmina",                         "capuchinho", None,      6),
    ("3031", "Capuchinho com Suporte de Corrente",           "capuchinho", None,      6),
    ("3034", "Capuchinho para Vidro",                        "capuchinho", None,      6),
    ("3036", "Capuchinho para Ferragem",                     "capuchinho", None,      22),
    ("3037", "Capuchinho para Fechadura",                    "capuchinho", None,      22),
    # ── Grupo 31 — DOBRADIÇAS (págs 7-9) ────────────────────────────────────
    ("3105", "Mancal Inferior para Porta",                   "pivo", None,            7),
    ("3106", "Mancal Inferior para Pivotante",               "pivo", None,            7),
    ("3107", "Mancal Superior e Lateral Retangular",         "pivo", None,            7),
    ("3110", "Dobradiça Inferior para Mola",                 "dobradica", "inferior", 7),
    ("3114", "Dobradiça Excêntrica Dir. Inf./Esq. Sup.",     "dobradica", None,       7),
    ("3115", "Dobradiça Excêntrica Esq. Inf./Dir. Sup.",     "dobradica", None,       7),
    ("3121", "Suporte Duplo para Dobradiça",                 "suporte", "dobradica",  7),
    ("3122", "Suporte de Batente",                           "batedor", None,         7),
    ("3123", "Suporte para Dobradiça para Porta Pivotante",  "suporte", "dobradica",  8),
    ("3124", "Suporte para Dobradiça com Excêntrico Dir.",   "suporte", "dobradica",  8),
    ("3125", "Suporte para Dobradiça com Excêntrico Esq.",   "suporte", "dobradica",  8),
    ("3128", "Suporte L em Ângulo Direito",                  "suporte", None,         8),
    ("3129", "Suporte L em Ângulo Esquerdo",                 "suporte", None,         8),
    ("3132", "Suporte L para Dobradiça",                     "suporte", "dobradica",  8),
    ("3134", "Suporte L Dir. para Dobradiça (Excêntrico)",   "suporte", "dobradica",  8),
    ("3135", "Suporte L Esq. para Dobradiça (Excêntrico)",   "suporte", "dobradica",  8),
    ("3140", "Dobradiça Superior e Inferior sem Mola",       "dobradica", None,       9),
    ("3141", "Dobradiça para Porta Pivotante",               "dobradica", None,       9),
    ("3143", "Dobradiça Vidro/Vidro",                        "dobradica", None,       9),
    ("3144", "Dobradiça de Batente",                         "dobradica", "batente",  9),
    ("3145", "Dobradiça para Porta Modelada Vidro/Vidro",    "dobradica", None,       9),
    ("3146", "Dobradiça Porta Modelada com Aba Reta",        "dobradica", None,       9),
    # ── Grupo 32 — TRINCOS E FECHADURAS (págs 10-12) ────────────────────────
    # 3210, 3211, 3212, 3230 já em canonicas → só variante
    ("3214", "Fechadura sem Tambor Externo",                 "fechadura", None,       10),
    ("3215", "Fechadura de Piso",                            "fechadura", None,       10),
    ("3232", "Espelho para Fechadura sem Aparador",          "contra_fechadura", None, 10),
    ("3240", "Trinco de Piso",                               "trinco", None,          10),
    ("3241", "Contra Pino de Piso",                          "contra_fechadura", None, 11),
    ("3246", "Contra Trinco Duplo",                          "contra_fechadura", None, 11),
    ("3248", "Trinco Superior para Porta Direito",           "trinco", None,          11),
    ("3249", "Trinco Superior para Porta Esquerdo",          "trinco", None,          11),
    ("3250", "Mini Trinco para Janela",                      "trinco", None,          11),
    ("3251", "Espelho para Trinco (para 3250)",              "contra_fechadura", None, 11),
    ("3252", "Contra Trinco (para 3250)",                    "contra_fechadura", None, 11),
    ("3253", "Suporte com Aparador",                         "suporte", None,         11),
    ("3254", "Batedor para Porta de Abrir",                  "batedor", None,         12),
    # ── Grupo 34 — BASCULANTES (págs 13-15) ─────────────────────────────────
    ("3401", "Dobradiça para Janela Basculante",             "dobradica", "basculante", 13),
    ("3402", "Suporte para Dobradiça de Janela Basculante",  "suporte", "dobradica",  13),
    ("3405", "Dobradiça para Janela Basculante Excêntrica",  "dobradica", "basculante", 13),
    ("3406", "Suporte para Dobr. de Jan. Basc. Excêntrica",  "suporte", "dobradica",  13),
    ("3407", "Corrente para Trinco",                         "corrente", None,         13),
    ("3408", "Suporte para Corrente",                        "suporte", None,          13),
    ("3410", "Trinco Sup. de Centro para Basculante",        "trinco", "basculante",   13),
    ("3411", "Contra Trinco de Centro para Basculante",      "contra_fechadura", None, 13),
    ("3412", "Trinco de Canto Dir. para Basc. (Completo)",   "trinco", "basculante",   14),
    ("3413", "Trinco de Canto Esq. para Basc. (Completo)",   "trinco", "basculante",   14),
    ("3414", "Espelho para Trinco de Basculante",            "contra_fechadura", None, 14),
    ("3415", "Trinco Inferior para Basculante",              "trinco", "basculante",   14),
    ("3416", "Dobradiça com Freio para Janela Basculante",   "dobradica", "basculante", 14),
    ("3417", "Suporte para Dobradiça com Freio",             "suporte", "dobradica",   14),
    ("3420", "Dobradiça para Pivotante (Pequena)",           "dobradica", None,        14),
    ("3421", "Suporte para Dobradiça Pivotante (Pequena)",   "suporte", "dobradica",   14),
    ("3424", "Dobradiça Jan. Proj. com Sup. Triplo Dir.",    "dobradica", None,        15),
    ("3425", "Dobradiça Jan. Proj. com Sup. Triplo Esq.",    "dobradica", None,        15),
    ("3426", "Suporte para Janela Projetante Direito",       "suporte", None,          15),
    ("3427", "Suporte para Janela Projetante Esquerdo",      "suporte", None,          15),
    ("3428", "Dobradiça para Janela Projetante Direito",     "dobradica", None,        15),
    ("3429", "Dobradiça para Janela Projetante Esquerdo",    "dobradica", None,        15),
    ("3438", "Dobradiça para Janela Basculante (Pequena)",   "dobradica", "basculante", 15),
    ("3439", "Suporte para Dobr. de Jan. Basc. (Pequena)",   "suporte", "dobradica",   15),
    # ── Grupo 35 — PORTAS DE CORRER (págs 16-17) ────────────────────────────
    # 3530, 3532, 3534, 3536 já em canonicas → só variante
    ("3501", "Dobradiça Superior para Porta Sanfonada",      "dobradica", None,        16),
    ("3502", "Dobradiça Inf. para Porta Sanfonada c/ Trinco","dobradica", None,        16),
    ("3503", "Carro Superior para Porta Sanfonada",          "carrinho", None,         16),
    ("3504", "Carro Inferior para Porta Sanfonada",          "carrinho", None,         16),
    ("3520", "Rodízio Excêntrico para Porta de Correr",      "roldana", None,          16),
    ("3539", "Trinco para Porta de Correr",                  "trinco", None,           17),
    ("3540", "Puxador para Porta de Correr",                 "puxador", None,          17),
    ("3541", "Contra Trinco Para Sistema de Correr Exp.",    "contra_fechadura", None, 17),
    ("3542", "Contra Trinco Para Sistema de Correr Emb.",    "contra_fechadura", None, 17),
    ("3543", "Contra Trinco para Sistema de Correr",         "contra_fechadura", None, 17),
    ("3544", "Contra Trinco 34mm",                           "contra_fechadura", None, 17),
    # ── Grupo 36 — BOX DE CORRER (pág 18) ───────────────────────────────────
    ("3611", "Suporte de Parede Esquerdo",                   "suporte", None,          18),
    ("3612", "Suporte de Parede Direito",                    "suporte", None,          18),
    ("3615", "Rodízio Excêntrico com Rolamento",             "roldana", None,          18),
    ("3637", "Puxador de Latão para Box",                    "puxador", None,          18),
    ("3638", "Puxador de Latão para Janela",                 "puxador", None,          18),
    ("3640", "Suporte Fixação Janela (porta)",               "suporte", None,          18),
    ("3641", "Suporte Fixação Janela (fixo)",                "suporte", None,          18),
    # ── Grupo 37 — BOX DE ABRIR (págs 19-20) ────────────────────────────────
    ("3701", "Dobradiça Automática Vidro/Vidro Esquerda",    "dobradica", "box",       19),
    ("3702", "Dobradiça Automática Vidro/Vidro Direita",     "dobradica", "box",       19),
    ("3703", "Dobradiça Automática de Batente Esquerda",     "dobradica", "box",       19),
    ("3704", "Dobradiça Automática de Batente Direita",      "dobradica", "box",       19),
    ("3713", "Dobradiça Automática Esquerda Pq. (1 furo)",   "dobradica", "box",       19),
    ("3714", "Dobradiça Automática Direita Pq. (1 furo)",    "dobradica", "box",       19),
    ("3715", "Dobradiça Automática Esquerda Pq. (2 furos)",  "dobradica", "box",       19),
    ("3716", "Dobradiça Automática Direita Pq. (2 furos)",   "dobradica", "box",       19),
    ("3730", "Cantoneira de Centro para Box",                "suporte", "cantoneira",  20),
    ("4718", "Dobradiça Europa para Box Esq/Dir",            "dobradica", "box",       20),
    # ── Grupo 38 — LINHA MINI (pág 21) ──────────────────────────────────────
    ("3830", "Espelho para Fechadura Mini com Aparador",     "contra_fechadura", None, 21),
    ("3832", "Fechadura Mini para Janela",                   "fechadura", None,         21),
    ("3836", "Contra Fechadura Mini",                        "contra_fechadura", None,  21),
]

# Códigos que já existem em canonicas (vindos de ferragens ETL v2)
# → apenas adiciona variante GMS, não cria novo canonical
_JA_EM_CANONICAS = frozenset({
    "3206", "3210", "3211", "3212", "3230",
    "3530", "3532", "3534", "3536",
})
# Para esses, o canonical_id + nome vieram do ETL v2; só precisamos da variante GMS
_VARIANTES_EXTRAS_GMS: list[tuple[str, str, int]] = [
    ("3210", "Fechadura de Centro",                      10),
    ("3211", "Contra Fechadura com Aparador",             10),
    ("3212", "Contra Fechadura sem Aparador",             10),
    ("3230", "Espelho para Fechadura com Aparador",       10),
    ("3530", "Fechadura para Porta de Correr",            16),
    ("3532", "Fechadura Porta de Correr sem Cilindro",    16),
    ("3534", "Contra Fechadura para Porta de Correr",     16),
    ("3536", "Contra Fechadura sem Puxador Externo",      17),
]

_PENDENTES = [
    {
        "descricao": "LGL — catálogo não disponível para download na data de ingestão",
        "contexto": '{"fonte": "ingestao_gms_blindex.py", "acao_sugerida": "Baixar PDF e rodar ingestao_lgl.py"}',
        "fonte": "phase_4_ingestao",
    },
    {
        "descricao": "TQ — catálogo não disponível para download na data de ingestão",
        "contexto": '{"fonte": "ingestao_gms_blindex.py", "acao_sugerida": "Baixar PDF e rodar ingestao_tq.py"}',
        "fonte": "phase_4_ingestao",
    },
]


def _linha_from_id(cid: str) -> str:
    import re
    if re.match(r"^1\d{3}$", cid):
        return "santa_marina_1000"
    if re.match(r"^[34]\d{3}$", cid):
        return "blindex_3000"
    return "outro"


# ─── ETL ──────────────────────────────────────────────────────────────────────

@dataclass
class GmsResult:
    canonicas_inserted: int = 0
    canonicas_skipped: int = 0
    variantes_inserted: int = 0
    variantes_skipped: int = 0
    pendentes_inserted: int = 0
    errors: list[str] = field(default_factory=list)


def run_ingestao(conn: sqlite3.Connection, dry_run: bool = True) -> GmsResult:
    result = GmsResult()

    existing = {r[0] for r in conn.execute("SELECT canonical_id FROM canonicas")}

    # ── 1. Novos canonicals ──────────────────────────────────────────────────
    for (cid, nome, cat, subcat, pag) in _GMS_ITEMS:
        if cid in _JA_EM_CANONICAS:
            continue  # já existe — só variante adiante

        log.debug("CANONICAL %s  %s", cid, nome[:45])

        if dry_run:
            result.canonicas_inserted += 1
        else:
            try:
                cur = conn.execute(
                    """INSERT OR IGNORE INTO canonicas
                       (canonical_id, linha, categoria, subcategoria,
                        nome_apresentacao, confidence, fontes_pdf)
                       VALUES (?, ?, ?, ?, ?, 'medio', ?)""",
                    (cid, _linha_from_id(cid), cat, subcat, nome,
                     f"gms_blindex p.{pag}"),
                )
                if cur.rowcount:
                    result.canonicas_inserted += 1
                else:
                    result.canonicas_skipped += 1
            except Exception as e:
                result.errors.append(f"canonical {cid}: {e}")

    # ── 2. Variantes GMS (novos + existentes) ────────────────────────────────
    all_variants: list[tuple[str, str, int]] = (
        [(cid, nome, pag) for (cid, nome, *_rest, pag) in _GMS_ITEMS]
        + _VARIANTES_EXTRAS_GMS
    )

    for (cid, nome, pag) in all_variants:
        vid = f"GMS_{cid}"
        log.debug("VARIANT  %s", vid)

        if dry_run:
            result.variantes_inserted += 1
            continue

        try:
            cur = conn.execute(
                """INSERT OR IGNORE INTO variantes_canonicas
                   (variant_id, canonical_id, fabricante_codigo,
                    codigo_original, nome_comercial,
                    fonte_pdf, pagina_pdf, extraction_quality)
                   VALUES (?, ?, 'GMS', ?, ?, 'gms_blindex', ?, 'parcial')""",
                (vid, cid, cid, nome, pag),
            )
            if cur.rowcount:
                result.variantes_inserted += 1
            else:
                result.variantes_skipped += 1
        except Exception as e:
            result.errors.append(f"variant {vid}: {e}")

    # ── 3. Pendentes (LGL + TQ) ──────────────────────────────────────────────
    log.info("PENDENTE LGL e TQ — sem arquivos disponíveis")
    if dry_run:
        result.pendentes_inserted = len(_PENDENTES)
    else:
        for p in _PENDENTES:
            try:
                cur = conn.execute(
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

    log.info("=== Ingestão GMS-Blindex — %s ===",
             "DRY-RUN" if dry_run else "APLICANDO")

    result = run_ingestao(conn, dry_run=dry_run)
    conn.close()

    log.info(
        "canonicas +%d skip=%d | variantes +%d skip=%d | "
        "pendentes=%d | erros=%d",
        result.canonicas_inserted, result.canonicas_skipped,
        result.variantes_inserted, result.variantes_skipped,
        result.pendentes_inserted, len(result.errors),
    )
    if result.errors:
        for e in result.errors:
            log.error("  %s", e)


if __name__ == "__main__":
    main()
