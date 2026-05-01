#!/usr/bin/env python3
"""
ingestao_glasspecas_2022.py — ingere dados do catálogo Glasspeças 2022.

Popula:
  - `canonicas`           → 4 canonical_ids ausentes do DB: 1126, 1128, 1320, 1326
  - `variantes_canonicas` → variantes dos 4 novos canonicals (SM/Glasspeças)
  - `regras_globais`      → 5 folgas NBR 7199
  - `kits_canonicos`      → 15 kits Glasspeças (1–18, exceto Kit 6 com extração falha)
  - `kits_componentes`    → componentes de cada kit (skip se canonical não existe)

Modo padrão: dry-run (apenas loga, não escreve).
Com --run: aplica ao banco.

Uso:
    python scripts/ingestao_glasspecas_2022.py
    python scripts/ingestao_glasspecas_2022.py --run
"""
from __future__ import annotations

import argparse
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

DEFAULT_DB = Path(__file__).parent.parent / "data" / "constitution.db"

# ─── Dados extraídos do catálogo Glasspeças 2022 (168 págs, Maio 2022) ───────

# 4 canonicals ausentes do DB (confirmados em confronto_vendedora_catalogos.md)
_NOVOS_CANONICALS = [
    {
        "canonical_id":    "1126",
        "linha":           "santa_marina_1000",
        "categoria":       "carrinho",
        "subcategoria":    "correr",
        "nome_apresentacao": "Carrinho para Porta de Correr",
        "confidence":      "alto",
        "fontes_pdf":      "glasspecas_2022 p.20-21",
        "obs":             "Família com 8+ variantes (B, M, MC, C, D, DC, DCR, QC). "
                           "Vendedora usa '126D' = variant 1126D.",
    },
    {
        "canonical_id":    "1128",
        "linha":           "santa_marina_1000",
        "categoria":       "dobradica",
        "subcategoria":    "horizontal",
        "nome_apresentacao": "Dobradiça Horizontal com Ponto de Giro a 65mm",
        "confidence":      "alto",
        "fontes_pdf":      "glasspecas_2022 p.22",
        "obs":             "Variantes A (lateral), B (canto), C (V/V). "
                           "Vendedora usa '128A/128B'.",
    },
    {
        "canonical_id":    "1320",
        "linha":           "santa_marina_1000",
        "categoria":       "suporte",
        "subcategoria":    "colante_passante",
        "nome_apresentacao": "Suporte sem Miolo e Cantoneira Central",
        "confidence":      "alto",
        "fontes_pdf":      "glasspecas_2022 p.35",
        "obs":             "Vem em versão Colante e Passante. "
                           "Vendedora usa '320 colante e 320 passante'.",
    },
    {
        "canonical_id":    "1326",
        "linha":           "santa_marina_1000",
        "categoria":       "suporte",
        "subcategoria":    "fixacao_vidro_fixo",
        "nome_apresentacao": "Suporte para Fixação de Vidro Fixo",
        "confidence":      "alto",
        "fontes_pdf":      "glasspecas_2022 p.38",
        "obs":             "Vendedora usa '326 mini'.",
    },
]

# Variantes dos 4 novos canonicals (source: Glasspeças, fab=SM)
_NOVAS_VARIANTES = [
    # 1126 family
    {"variant_id": "SM_1126B",   "canonical_id": "1126", "fabricante_codigo": "SM",
     "codigo_original": "1126B",   "nome_comercial": "Carrinho de Rolamento Meia Cana",
     "dimensoes_variantes_json": '{"dim_max_largura_mm": 500, "dim_max_altura_mm": 1400, "espessura_vidro": "8mm", "material": "Latão"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 20},
    {"variant_id": "SM_1126M",   "canonical_id": "1126", "fabricante_codigo": "SM",
     "codigo_original": "1126M",   "nome_comercial": "Mini Carrinho para Porta de Correr com Rolamento Meia Cana",
     "dimensoes_variantes_json": '{"dim_max_largura_mm": 500, "dim_max_altura_mm": 1500, "espessura_vidro": "8mm", "material": "Zamac"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 20},
    {"variant_id": "SM_1126MC",  "canonical_id": "1126", "fabricante_codigo": "SM",
     "codigo_original": "1126MC",  "nome_comercial": "Mini Carrinho para Porta de Correr com Rolamento Côncavo",
     "dimensoes_variantes_json": '{"dim_max_largura_mm": 500, "dim_max_altura_mm": 1500, "espessura_vidro": "8mm", "material": "Zamac"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 20},
    {"variant_id": "SM_1126C",   "canonical_id": "1126", "fabricante_codigo": "SM",
     "codigo_original": "1126C",   "nome_comercial": "Carrinho para Porta de Correr com Rolamento Côncavo",
     "dimensoes_variantes_json": '{"dim_max_largura_mm": 600, "dim_max_altura_mm": 1800, "espessura_vidro": "8-10mm", "material": "Zamac"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 20},
    {"variant_id": "SM_1126D",   "canonical_id": "1126", "fabricante_codigo": "SM",
     "codigo_original": "1126D",   "nome_comercial": "Carrinho Duplo para Porta de Correr com Rolamento Meia Cana",
     "dimensoes_variantes_json": '{"dim_max_largura_mm": 700, "dim_max_altura_mm": 2100, "espessura_vidro": "10mm", "material": "Zamac"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 20},
    {"variant_id": "SM_1126",    "canonical_id": "1126", "fabricante_codigo": "SM",
     "codigo_original": "1126",    "nome_comercial": "Carrinho Duplo para Porta de Correr (Zamac/Latão)",
     "dimensoes_variantes_json": '{"dim_max_largura_mm": 1000, "dim_max_altura_mm": 2800, "espessura_vidro": "8-10mm", "material": "Zamac/Latão"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 21},
    {"variant_id": "SM_1126DCR", "canonical_id": "1126", "fabricante_codigo": "SM",
     "codigo_original": "1126DCR", "nome_comercial": "Carrinho Duplo para Porta de Correr com Rolamento Côncavo Reforçado",
     "dimensoes_variantes_json": '{"dim_max_largura_mm": 900, "dim_max_altura_mm": 2700, "espessura_vidro": "8-10mm", "material": "Aço"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 21},
    {"variant_id": "SM_1126QC",  "canonical_id": "1126", "fabricante_codigo": "SM",
     "codigo_original": "1126QC",  "nome_comercial": "Carrinho Quádruplo Côncavo",
     "dimensoes_variantes_json": '{"dim_max_largura_mm": 1200, "dim_max_altura_mm": 3000, "espessura_vidro": "8-10mm", "material": "Latão"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 21},
    {"variant_id": "SM_1126DC",  "canonical_id": "1126", "fabricante_codigo": "SM",
     "codigo_original": "1126DC",  "nome_comercial": "Carrinho Duplo para Porta de Correr com Rolamento Côncavo",
     "dimensoes_variantes_json": '{"espessura_vidro": "8-10mm", "material": "Zamac"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 21},
    # 1128 family
    {"variant_id": "SM_1128A",   "canonical_id": "1128", "fabricante_codigo": "SM",
     "codigo_original": "1128A",   "nome_comercial": "Dobradiça Lateral Horizontal com Ponto de Giro a 65mm",
     "dimensoes_variantes_json": '{"dim_max_largura_mm": 1000, "dim_max_altura_mm": 2100, "espessura_vidro": "8-10mm", "material": "Latão"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 22},
    {"variant_id": "SM_1128B",   "canonical_id": "1128", "fabricante_codigo": "SM",
     "codigo_original": "1128B",   "nome_comercial": "Dobradiça Horizontal de Canto com Ponto de Giro a 65mm",
     "dimensoes_variantes_json": '{"dim_max_largura_mm": 1000, "dim_max_altura_mm": 2100, "espessura_vidro": "8-10mm", "material": "Latão"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 22},
    {"variant_id": "SM_1128C",   "canonical_id": "1128", "fabricante_codigo": "SM",
     "codigo_original": "1128C",   "nome_comercial": "Dobradiça Horizontal V/V com Ponto de Giro a 65mm",
     "dimensoes_variantes_json": '{"espessura_vidro": "8-10mm", "material": "Latão"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 22},
    # 1320 e 1326
    {"variant_id": "SM_1320G",   "canonical_id": "1320", "fabricante_codigo": "SM",
     "codigo_original": "1320G",   "nome_comercial": "Suporte sem Miolo e Cantoneira Central (Colante e Passante)",
     "dimensoes_variantes_json": '{"espessura_vidro": "8-10mm", "material": "Zamac"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 35},
    {"variant_id": "SM_1326G",   "canonical_id": "1326", "fabricante_codigo": "SM",
     "codigo_original": "1326G",   "nome_comercial": "Suporte para Fixação de Vidro Fixo",
     "dimensoes_variantes_json": '{"espessura_vidro": "8-10mm", "material": "Zamac", "pino": "aço"}',
     "fonte_pdf": "glasspecas_2022", "pagina_pdf": 38},
]

# Folgas NBR 7199 (extraídas literalmente do catálogo p.9 / NBR 7199)
_REGRAS_NBR = [
    {
        "regra_id":       "folga_movel_fixo",
        "categoria":      "folga_nbr",
        "descricao":      "Folga mínima entre peças móveis e fixas",
        "valor_numerico": 3.0,
        "unidade":        "mm",
        "fonte":          "NBR 7199 / Glasspeças 2022 p.9",
    },
    {
        "regra_id":       "folga_movel_movel",
        "categoria":      "folga_nbr",
        "descricao":      "Folga mínima entre peças móveis",
        "valor_numerico": 4.0,
        "unidade":        "mm",
        "fonte":          "NBR 7199 / Glasspeças 2022 p.9",
    },
    {
        "regra_id":       "folga_movel_piso",
        "categoria":      "folga_nbr",
        "descricao":      "Folga mínima entre peça móvel e piso",
        "valor_numerico": 8.0,
        "unidade":        "mm",
        "fonte":          "NBR 7199 / Glasspeças 2022 p.9",
    },
    {
        "regra_id":       "folga_fixo_fixo",
        "categoria":      "folga_nbr",
        "descricao":      "Folga mínima entre peças fixas",
        "valor_numerico": 1.0,
        "unidade":        "mm",
        "fonte":          "NBR 7199 / Glasspeças 2022 p.9",
    },
    {
        "regra_id":       "folga_movel_alvenaria",
        "categoria":      "folga_nbr",
        "descricao":      "Folga mínima entre peça móvel e lateral de alvenaria",
        "valor_numerico": 5.0,
        "unidade":        "mm",
        "fonte":          "NBR 7199 / Glasspeças 2022 p.9",
    },
]

# Mapeamento de código de catálogo → canonical_id
# Padrão: strip sufixos de cor/variante, pega os 4 dígitos iniciais
def _canon(codigo: str) -> str:
    m = re.match(r"^(\d{4})", codigo)
    return m.group(1) if m else codigo


# Kits Glasspeças 2022 (págs. 147-152)
# Cada componente: (codigo_catalogo, quantidade)
_KITS = [
    {
        "kit_id": "GLP_KIT01", "nome": "Kit 1 — Porta Simples Pivotante",
        "tipologia": "porta_pivotante", "fonte_pdf": "glasspecas_2022 p.147",
        "componentes": [
            ("1201SG", 1), ("1101SG", 1), ("1103SG", 1),
            ("1013SG", 1), ("1520G", 1), ("1504AG", 1),
        ],
    },
    {
        "kit_id": "GLP_KIT02", "nome": "Kit 2 — Janela Pivotante",
        "tipologia": "janela_pivotante", "fonte_pdf": "glasspecas_2022 p.147",
        "componentes": [
            ("1201SG", 2), ("1230G", 2), ("1335G", 1), ("1038G", 1),
        ],
    },
    {
        "kit_id": "GLP_KIT03", "nome": "Kit 3 — Janela de Correr com 4 Folhas",
        "tipologia": "janela_correr", "fonte_pdf": "glasspecas_2022 p.147",
        "componentes": [
            ("1038BG", 2), ("1335G", 2), ("1629JG", 2),
        ],
    },
    {
        "kit_id": "GLP_KIT04", "nome": "Kit 4 — Janela de Correr com 2 Folhas",
        "tipologia": "janela_correr", "fonte_pdf": "glasspecas_2022 p.148",
        "componentes": [
            ("1038BG", 1), ("1335G", 1), ("1629JG", 1),
        ],
    },
    {
        "kit_id": "GLP_KIT05", "nome": "Kit 5 — Box de Abrir VA",
        "tipologia": "box_abrir", "fonte_pdf": "glasspecas_2022 p.148",
        "componentes": [
            ("1114G", 2), ("1629BG", 1),
        ],
    },
    # Kit 6: extração de PDF falhou (conteúdo misturado com Kit 4)
    # Inserido sem componentes; marcado como pendente
    {
        "kit_id": "GLP_KIT06", "nome": "Kit 6 — Basculante VA Pequeno",
        "tipologia": "basculante_va", "fonte_pdf": "glasspecas_2022 p.148",
        "obs": "Componentes não extraídos — layout de página corrompeu o texto no PDF.",
        "componentes": [],
    },
    {
        "kit_id": "GLP_KIT07", "nome": "Kit 7 — Basculante VA Grande",
        "tipologia": "basculante_va", "fonte_pdf": "glasspecas_2022 p.148",
        "componentes": [
            ("1201SG", 2), ("1231G", 2), ("1523G", 1),
            ("1801G", 1), ("1003G", 1), ("1003AG", 2), ("1005G", 1),
        ],
    },
    {
        "kit_id": "GLP_KIT08", "nome": "Kit 8 — Porta Dupla Pivotante",
        "tipologia": "porta_pivotante", "fonte_pdf": "glasspecas_2022 p.149",
        "componentes": [
            ("1201SG", 2), ("1101SG", 2), ("1103SG", 2),
            ("1013SG", 2), ("1520G", 1), ("1531G", 1),
            ("1335G", 1), ("1038G", 1),
        ],
    },
    {
        "kit_id": "GLP_KIT09", "nome": "Kit 9 — Porta de Correr Vidro Linha 3000",
        "tipologia": "porta_correr", "fonte_pdf": "glasspecas_2022 p.149",
        "componentes": [("3530G", 1), ("3534G", 1)],
    },
    {
        "kit_id": "GLP_KIT10", "nome": "Kit 10 — Porta de Correr Alvenaria Linha 3000",
        "tipologia": "porta_correr", "fonte_pdf": "glasspecas_2022 p.150",
        "componentes": [("3530G", 1), ("3230G", 1)],
    },
    {
        "kit_id": "GLP_KIT11", "nome": "Kit 11 — Janela de Correr Vidro Linha 3000",
        "tipologia": "janela_correr", "fonte_pdf": "glasspecas_2022 p.150",
        "componentes": [("3532G", 1), ("3536G", 1)],
    },
    {
        "kit_id": "GLP_KIT12", "nome": "Kit 12 — Janela de Correr Alvenaria Linha 3000",
        "tipologia": "janela_correr", "fonte_pdf": "glasspecas_2022 p.150",
        "componentes": [("3532G", 1), ("3230G", 1)],
    },
    {
        "kit_id": "GLP_KIT13", "nome": "Kit 13 — Basculante VV Pequeno",
        "tipologia": "basculante_vv", "fonte_pdf": "glasspecas_2022 p.150",
        "componentes": [
            ("1123G", 2), ("1230G", 2), ("1523G", 1),
            ("1801G", 1), ("1003G", 1), ("1003AG", 2), ("1005G", 1),
        ],
    },
    {
        "kit_id": "GLP_KIT14", "nome": "Kit 14 — Basculante/Fixo Basculante",
        "tipologia": "basculante_vv", "fonte_pdf": "glasspecas_2022 p.151",
        "componentes": [
            ("1201SG", 2), ("1230G", 4), ("1123G", 2), ("1523G", 2),
            ("1801G", 2), ("1003G", 2), ("1003AG", 4), ("1005G", 2),
        ],
    },
    {
        "kit_id": "GLP_KIT15", "nome": "Kit 15 — Porta Pivotante (PGA)",
        "tipologia": "porta_pivotante", "fonte_pdf": "glasspecas_2022 p.151",
        "componentes": [("1101PGAG", 1), ("1103PGAG", 1), ("1201G", 1)],
    },
    {
        "kit_id": "GLP_KIT16", "nome": "Kit 16 — Porta Pivotante com Fechadura MA",
        "tipologia": "porta_pivotante", "fonte_pdf": "glasspecas_2022 p.151",
        "componentes": [
            ("1201SG", 1), ("1101SG", 1), ("1013SG", 1),
            ("1520MAG", 1), ("1103SG", 1), ("1506AUG", 1),
        ],
    },
    # Kits 17-18 referenciam produtos da Linha 3000 extended (3107, 3140, 3105, 3438, 3410, 3414)
    # que não existem no DB atual — inseridos sem componentes, marcados como pendentes
    {
        "kit_id": "GLP_KIT17", "nome": "Kit 17 — Basculante VA Pequeno Linha 3000",
        "tipologia": "basculante_va", "fonte_pdf": "glasspecas_2022 p.152",
        "obs": "Componentes 3107G, 3438G, 3410G, 3414G não estão no DB (Linha 3000 extended).",
        "componentes": [("3107G", 2), ("3438G", 2), ("3410G", 1), ("3414G", 1)],
    },
    {
        "kit_id": "GLP_KIT18", "nome": "Kit 18 — Porta Simples Pivotante Linha 3000",
        "tipologia": "porta_pivotante", "fonte_pdf": "glasspecas_2022 p.152",
        "obs": "Componentes 3107G, 3140G, 3105G não estão no DB (Linha 3000 extended).",
        "componentes": [("3107G", 1), ("3140G", 2), ("3105G", 1), ("3210G", 1), ("3230G", 1)],
    },
]


# ─── ETL ──────────────────────────────────────────────────────────────────────

@dataclass
class IngestaoResult:
    canonicas_inserted: int = 0
    canonicas_skipped: int = 0
    variantes_inserted: int = 0
    variantes_skipped: int = 0
    regras_inserted: int = 0
    regras_skipped: int = 0
    kits_inserted: int = 0
    kits_skipped: int = 0
    componentes_inserted: int = 0
    componentes_skipped: int = 0
    componentes_missing_canonical: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _existing_canonicals(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT canonical_id FROM canonicas")}


def run_ingestao(conn: sqlite3.Connection, dry_run: bool = True) -> IngestaoResult:
    result = IngestaoResult()
    existing = _existing_canonicals(conn)

    # ── 1. Novos canonicals ──────────────────────────────────────────────────
    for c in _NOVOS_CANONICALS:
        cid = c["canonical_id"]
        log.info("CANONICAL %s  %s", cid, c["nome_apresentacao"][:50])
        if dry_run:
            result.canonicas_inserted += 1
            continue
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
                result.canonicas_inserted += 1
            else:
                result.canonicas_skipped += 1
        except Exception as e:
            result.errors.append(f"canonical {cid}: {e}")

    # ── 2. Variantes dos novos canonicals ────────────────────────────────────
    for v in _NOVAS_VARIANTES:
        vid = v["variant_id"]
        log.debug("VARIANT %s  (%s)", vid, v["codigo_original"])
        if dry_run:
            result.variantes_inserted += 1
            continue
        try:
            cur = conn.execute(
                """INSERT OR IGNORE INTO variantes_canonicas
                   (variant_id, canonical_id, fabricante_codigo,
                    codigo_original, nome_comercial,
                    dimensoes_variantes_json, fonte_pdf, pagina_pdf,
                    extraction_quality)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completo')""",
                (vid, v["canonical_id"], v["fabricante_codigo"],
                 v["codigo_original"], v["nome_comercial"],
                 v.get("dimensoes_variantes_json"),
                 v.get("fonte_pdf"), v.get("pagina_pdf")),
            )
            if cur.rowcount:
                result.variantes_inserted += 1
            else:
                result.variantes_skipped += 1
        except Exception as e:
            result.errors.append(f"variant {vid}: {e}")

    # ── 3. Regras globais (folgas NBR) ───────────────────────────────────────
    for r in _REGRAS_NBR:
        log.info("REGRA  %s = %smm", r["regra_id"], r["valor_numerico"])
        if dry_run:
            result.regras_inserted += 1
            continue
        try:
            cur = conn.execute(
                """INSERT OR IGNORE INTO regras_globais
                   (regra_id, categoria, descricao, valor_numerico, unidade, fonte)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (r["regra_id"], r["categoria"], r["descricao"],
                 r["valor_numerico"], r["unidade"], r["fonte"]),
            )
            if cur.rowcount:
                result.regras_inserted += 1
            else:
                result.regras_skipped += 1
        except Exception as e:
            result.errors.append(f"regra {r['regra_id']}: {e}")

    # Refresh existing após inserir os 4 novos canonicals
    if not dry_run:
        existing = _existing_canonicals(conn)

    # ── 4. Kits ───────────────────────────────────────────────────────────────
    for kit in _KITS:
        kid = kit["kit_id"]
        log.info("KIT    %s  %s", kid, kit["nome"])
        if dry_run:
            result.kits_inserted += 1
            result.componentes_inserted += len(kit["componentes"])
            continue
        try:
            cur = conn.execute(
                """INSERT OR IGNORE INTO kits_canonicos
                   (kit_id, nome, tipologia, fabricante_origem, fonte_pdf, obs)
                   VALUES (?, ?, ?, 'SM', ?, ?)""",
                (kid, kit["nome"], kit["tipologia"],
                 kit.get("fonte_pdf"), kit.get("obs")),
            )
            if cur.rowcount:
                result.kits_inserted += 1
            else:
                result.kits_skipped += 1
                continue  # kit já existe, pula componentes
        except Exception as e:
            result.errors.append(f"kit {kid}: {e}")
            continue

        for codigo_cat, qty in kit["componentes"]:
            cid = _canon(codigo_cat)
            if cid not in existing:
                log.warning(
                    "KIT    %s: componente %s → canonical '%s' não existe no DB (skip)",
                    kid, codigo_cat, cid,
                )
                result.componentes_missing_canonical.append(f"{kid}:{codigo_cat}")
                continue
            try:
                cur2 = conn.execute(
                    """INSERT OR IGNORE INTO kits_componentes
                       (kit_id, canonical_id, quantidade, obrigatorio)
                       VALUES (?, ?, ?, 1)""",
                    (kid, cid, qty),
                )
                if cur2.rowcount:
                    result.componentes_inserted += 1
                else:
                    result.componentes_skipped += 1
            except Exception as e:
                result.errors.append(f"comp {kid}×{cid}: {e}")

    if not dry_run:
        conn.commit()

    return result


# ─── Entrypoint ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Aplica (padrão: dry-run)")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()

    dry_run = not args.run
    db_path = Path(args.db)

    if not db_path.exists():
        log.error("DB não encontrado: %s", db_path)
        raise SystemExit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    log.info("=== Ingestão Glasspeças 2022 — %s ===",
             "DRY-RUN" if dry_run else "APLICANDO")

    result = run_ingestao(conn, dry_run=dry_run)
    conn.close()

    log.info(
        "canonicas +%d skip=%d | variantes +%d skip=%d | "
        "regras +%d skip=%d | kits +%d skip=%d | "
        "componentes +%d skip=%d missing=%d | erros=%d",
        result.canonicas_inserted, result.canonicas_skipped,
        result.variantes_inserted, result.variantes_skipped,
        result.regras_inserted, result.regras_skipped,
        result.kits_inserted, result.kits_skipped,
        result.componentes_inserted, result.componentes_skipped,
        len(result.componentes_missing_canonical),
        len(result.errors),
    )
    if result.componentes_missing_canonical:
        for m in result.componentes_missing_canonical:
            log.warning("MISSING  %s", m)


if __name__ == "__main__":
    main()
