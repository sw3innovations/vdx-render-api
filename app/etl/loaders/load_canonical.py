"""CanonicalLoader — reads staging tables, writes canonical tables."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from app.core.constitution import _get_conn
from app.etl.normalizers.canonical_materials import normalizar_material, SEED_MATERIAIS
from app.etl.normalizers.canonical_acabamentos import normalizar_acabamento, SEED_ACABAMENTOS
from app.etl.normalizers.canonical_variaveis import SEED_VARIAVEIS, normalizar_variavel, _eixo_from_codigo
from app.etl.normalizers.canonical_tipologias import ds_tmd_to_codigo, inferir_categoria
from app.etl.transformers.inference import inferir_nome_modelo, inferir_nome_valido
from app.etl.transformers.formula_parser import normalizar_formula
from app.etl.transformers.deduplicator import normalizar_codigo_ferragem
from app.etl.transformers import linker


@dataclass
class ETLStats:
    materiais: int = 0
    acabamentos: int = 0
    variaveis: int = 0
    tipologias: int = 0
    modelos: int = 0
    pecas_geometria: int = 0
    ferragens: int = 0
    auditoria_entries: int = 0
    erros: list[str] = field(default_factory=list)


class CanonicalLoader:
    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self._conn = conn or _get_conn()
        self._owned = conn is None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        if self._owned:
            self._conn.close()

    # ── public API ────────────────────────────────────────────────────────────

    def run(self) -> ETLStats:
        stats = ETLStats()
        self._seed_lookup_tables(stats)
        self._load_tipologias(stats)
        self._load_modelos(stats)
        self._load_pecas_geometria(stats)
        self._load_ferragens_catalogo(stats)
        self._conn.commit()
        self._log_audit(stats)
        return stats

    def reset(self) -> None:
        """Truncate all canonical tables (for re-run)."""
        tables = [
            "pecas_geometria_canonicas",
            "ferragens_aliases",
            "ferragens_canonicas",
            "modelos_canonicos",
            "tipologias_canonicas",
            "variaveis_aliases",
            "variaveis_canonicas",
            "acabamentos_aliases",
            "acabamentos_canonicos",
            "materiais_aliases",
            "materiais_canonicos",
            "etl_auditoria",
        ]
        for t in tables:
            self._conn.execute(f"DELETE FROM {t}")
        self._conn.commit()

    # ── lookup seeds ──────────────────────────────────────────────────────────

    def _seed_lookup_tables(self, stats: ETLStats) -> None:
        # materiais
        for codigo, nome, densidade in SEED_MATERIAIS:
            self._conn.execute(
                "INSERT OR IGNORE INTO materiais_canonicos (codigo, nome_apresentacao, densidade_kg_m3) VALUES (?,?,?)",
                (codigo, nome, densidade),
            )
            stats.materiais += 1

        # acabamentos
        for codigo, nome in SEED_ACABAMENTOS:
            self._conn.execute(
                "INSERT OR IGNORE INTO acabamentos_canonicos (codigo, nome_apresentacao) VALUES (?,?)",
                (codigo, nome),
            )
            stats.acabamentos += 1

        # variaveis
        for codigo, nome, eixo in SEED_VARIAVEIS:
            self._conn.execute(
                "INSERT OR IGNORE INTO variaveis_canonicas (codigo, nome_apresentacao, eixo) VALUES (?,?,?)",
                (codigo, nome, eixo),
            )
            stats.variaveis += 1

    # ── tipologias ────────────────────────────────────────────────────────────

    def _load_tipologias(self, stats: ETLStats) -> None:
        # Seed a fallback tipologia for models without nu_tip
        self._conn.execute(
            """INSERT OR IGNORE INTO tipologias_canonicas
               (codigo, nome_apresentacao, categoria, nu_tip_dump, fonte_origem)
               VALUES (?,?,?,?,?)""",
            ("SEM_TIPOLOGIA", "Sem Tipologia", None, None, "etl_fallback"),
        )
        rows = self._conn.execute(
            "SELECT nu_tip, ds_tmd, id_ativo FROM dump_tipologias ORDER BY nu_tip"
        ).fetchall()
        for nu_tip, ds_tmd, id_ativo in rows:
            codigo = ds_tmd_to_codigo(nu_tip, ds_tmd)
            categoria = inferir_categoria(ds_tmd)
            self._conn.execute(
                """INSERT OR IGNORE INTO tipologias_canonicas
                   (codigo, nome_apresentacao, categoria, nu_tip_dump, fonte_origem)
                   VALUES (?,?,?,?,?)""",
                (codigo, ds_tmd or f"Tipologia {nu_tip}", categoria, nu_tip, "dump_vdx"),
            )
            stats.tipologias += 1

    # ── modelos ───────────────────────────────────────────────────────────────

    def _load_modelos(self, stats: ETLStats) -> None:
        rows = self._conn.execute(
            "SELECT nu_mod, nu_tip, ds_mod, div_largura, div_altura FROM dump_modelos ORDER BY nu_mod"
        ).fetchall()
        _fallback_tip_id: int | None = None

        for nu_mod, nu_tip, ds_mod, div_largura, div_altura in rows:
            tip_id = linker.lookup_tipologia_id(self._conn, nu_tip) if nu_tip else None
            if tip_id is None:
                # Use fallback tipologia for models without nu_tip association
                if _fallback_tip_id is None:
                    row = self._conn.execute(
                        "SELECT id FROM tipologias_canonicas WHERE codigo='SEM_TIPOLOGIA'"
                    ).fetchone()
                    _fallback_tip_id = row[0] if row else None
                tip_id = _fallback_tip_id
            if tip_id is None:
                stats.erros.append(f"modelo {nu_mod}: sem tipologia e fallback não encontrado")
                continue
            nome_valido = inferir_nome_valido(ds_mod)
            nome = ds_mod if nome_valido else None
            nome_inferido = not nome_valido
            if not nome_valido:
                tip_row = self._conn.execute(
                    "SELECT ds_tmd FROM dump_tipologias WHERE nu_tip=?", (nu_tip,)
                ).fetchone()
                ds_tmd = tip_row[0] if tip_row else None
                nome = inferir_nome_modelo(nu_mod, ds_tmd, div_largura or 1, div_altura or 1)
            self._conn.execute(
                """INSERT OR IGNORE INTO modelos_canonicos
                   (tipologia_id, nu_mod_dump, nome, nome_inferido, largura_div, altura_div, fonte_origem)
                   VALUES (?,?,?,?,?,?,?)""",
                (tip_id, nu_mod, nome, int(nome_inferido), div_largura, div_altura, "dump_vdx"),
            )
            stats.modelos += 1

    # ── peças geometria ───────────────────────────────────────────────────────

    def _load_pecas_geometria(self, stats: ETLStats) -> None:
        rows = self._conn.execute(
            """SELECT nu_mod, nu_peca, ds_peca, ds_tipo,
                      eixo_x_alt, eixo_y_alt, eixo_x_lar, eixo_y_lar,
                      ds_formula_alt, ds_formula_lar
               FROM dump_geometria_pecas ORDER BY nu_mod, nu_peca"""
        ).fetchall()
        for nu_mod, nu_peca, ds_peca, ds_tipo, ex_alt, ey_alt, ex_lar, ey_lar, f_alt, f_lar in rows:
            mod_id = linker.lookup_modelo_id(self._conn, nu_mod)
            if mod_id is None:
                stats.erros.append(f"peca ({nu_mod},{nu_peca}): modelo não encontrado")
                continue
            self._conn.execute(
                """INSERT OR IGNORE INTO pecas_geometria_canonicas
                   (modelo_id, nu_peca, ds_peca, tipo_peca,
                    eixo_x_alt, eixo_y_alt, eixo_x_larg, eixo_y_larg,
                    formula_alt_original, formula_alt_normalizada,
                    formula_larg_original, formula_larg_normalizada,
                    fonte_origem)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    mod_id, nu_peca, ds_peca, ds_tipo,
                    ex_alt, ey_alt, ex_lar, ey_lar,
                    f_alt, normalizar_formula(f_alt),
                    f_lar, normalizar_formula(f_lar),
                    "dump_vdx",
                ),
            )
            stats.pecas_geometria += 1

    # ── ferragens do catálogo PDF ─────────────────────────────────────────────

    def _load_ferragens_catalogo(self, stats: ETLStats) -> None:
        rows = self._conn.execute(
            """SELECT p.id, p.codigo, p.nome, p.tipo_visual, p.material,
                      p.acabamento, p.comp_mm, p.diametro_mm, f.codigo as fab_codigo
               FROM catalogo_puxadores p
               JOIN catalogo_fabricantes f ON f.codigo = p.fabricante_id"""
        ).fetchall()
        for row_id, codigo, nome, tipo_visual, material, acabamento, comp_mm, diam_mm, fab_codigo in rows:
            codigo_norm = normalizar_codigo_ferragem(codigo)
            mat_codigo = normalizar_material(material)
            acab_codigo = normalizar_acabamento(acabamento)
            mat_id = linker.lookup_material_id(self._conn, mat_codigo)
            acab_id = linker.lookup_acabamento_id(self._conn, acab_codigo)

            self._conn.execute(
                """INSERT OR IGNORE INTO ferragens_canonicas
                   (codigo_normalizado, tipo, nome_apresentacao,
                    material_id, acabamento_id, fabricante_codigo,
                    comprimento_mm, diametro_mm, fontes_json)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    codigo_norm, tipo_visual, nome,
                    mat_id, acab_id, fab_codigo,
                    comp_mm, diam_mm,
                    json.dumps(["catalogo_pdf"]),
                ),
            )
            stats.ferragens += 1

    # ── auditoria ─────────────────────────────────────────────────────────────

    def _log_audit(self, stats: ETLStats) -> None:
        entries = [
            ("seed_lookups",   "CanonicalLoader", "materiais_canonicos",      stats.materiais,   stats.materiais,   0),
            ("seed_lookups",   "CanonicalLoader", "acabamentos_canonicos",     stats.acabamentos, stats.acabamentos, 0),
            ("seed_lookups",   "CanonicalLoader", "variaveis_canonicas",       stats.variaveis,   stats.variaveis,   0),
            ("load_tipologias","CanonicalLoader", "tipologias_canonicas",      stats.tipologias,  stats.tipologias,  0),
            ("load_modelos",   "CanonicalLoader", "modelos_canonicos",         stats.modelos,     stats.modelos,     len(stats.erros)),
            ("load_pecas",     "CanonicalLoader", "pecas_geometria_canonicas", stats.pecas_geometria, stats.pecas_geometria, 0),
            ("load_ferragens", "CanonicalLoader", "ferragens_canonicas",       stats.ferragens,   stats.ferragens,   0),
        ]
        for estagio, transformer, tabela, processados, aceitos, rejeitados in entries:
            self._conn.execute(
                """INSERT INTO etl_auditoria
                   (estagio, transformer, tabela_destino, registros_processados,
                    registros_aceitos, registros_rejeitados, motivos_rejeicao_json)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    estagio, transformer, tabela,
                    processados, aceitos, rejeitados,
                    json.dumps(stats.erros) if stats.erros else None,
                ),
            )
        self._conn.commit()
        stats.auditoria_entries = len(entries)
