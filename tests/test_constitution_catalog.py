"""
Testes de sanidade: Constitution populada com dados dos catálogos de ferragens.

Rode com: python -m pytest tests/test_constitution_catalog.py -v

IMPORTANTE: Rodar `python -m tools.catalog_loader` antes dos testes para popular o DB.
"""
import sqlite3
import sys
from pathlib import Path
import pytest

# Garante que o root do projeto está no sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.constitution import (
    buscar_kit, buscar_ferragem, buscar_equivalentes,
    buscar_recortes, listar_kits, get_stats, migrate,
    buscar_folga_nbr, todas_folgas_nbr, normalizar_formula,
    DB_PATH,
)
from tools.catalog_loader import (
    CatalogLoader, GLASSPECAS_DATA,
    inferir_tipo_recorte, parse_recorte_multi_contexto, _is_multi_context_recorte,
)


@pytest.fixture(scope="session", autouse=True)
def popular_db():
    """Popula o DB com dados dos catálogos antes de rodar os testes."""
    migrate()
    with CatalogLoader(dry_run=False) as loader:
        loader.carregar_glasspecas()
        # HELA e AL só se os JSONs existirem
        loader.carregar_hela()
        loader.carregar_al()
        loader.carregar_equivalencias_cross()
    yield


hela_disponivel = pytest.mark.skipif(
    not (ROOT / "data" / "catalogs" / "catalogo_hela.json").exists(),
    reason="catalogo_hela.json não disponível em data/catalogs/"
)


class TestKit01HELA:
    @hela_disponivel
    def test_kit_01_hela_existe(self):
        kits = buscar_kit("01", "HE")
        assert len(kits) >= 1, "Kit 01 da HELA não encontrado"

    @hela_disponivel
    def test_kit_01_hela_tem_componentes(self):
        """Kit 01 HELA deve ter componentes"""
        kits = buscar_kit("01", "HE")
        assert len(kits) >= 1
        kit = kits[0]
        assert len(kit["componentes"]) >= 1, (
            f"Kit 01 HELA sem componentes. Kit: {kit}"
        )


class TestKit01Glasspecas:
    def test_kit_01_sm_existe(self):
        kits = buscar_kit("01", "SM")
        assert len(kits) == 1, "Kit 01 Glasspeças não encontrado"

    def test_kit_01_sm_tem_6_componentes(self):
        """Kit 01 Glasspeças deve ter 6 componentes."""
        kits = buscar_kit("01", "SM")
        assert len(kits) == 1
        componentes = kits[0]["componentes"]
        assert len(componentes) == 6, (
            f"Esperado 6 componentes, encontrado {len(componentes)}: {componentes}"
        )

    def test_kit_01_componentes_corretos(self):
        """Kit 01 SM deve ter os códigos corretos."""
        kits = buscar_kit("01", "SM")
        codigos = {c["ferragem_codigo"] for c in kits[0]["componentes"]}
        esperados = {"1201SG", "1101SG", "1103SG", "1013SG", "1520G", "1504AG"}
        assert codigos == esperados, f"Componentes incorretos: {codigos}"


class TestKitCrossReference:
    def test_kit_01_cross_reference(self):
        """Kit 01 deve existir no SM pelo menos."""
        kits_sm = buscar_kit("01", "SM")
        assert len(kits_sm) >= 1, "Kit 01 não encontrado no SM"

    def test_todos_os_kits_listagem(self):
        """listar_kits deve retornar pelo menos os kits do SM."""
        kits = listar_kits("SM")
        assert len(kits) >= 1, "Nenhum kit encontrado para SM"


class TestEquivalencias:
    def test_equivalencia_1101(self):
        """Dobradiça 1101: SM=1101SG, HE=HE 1101A, AL=1101A"""
        equivs = buscar_equivalentes("1101")
        assert len(equivs) >= 1, "Nenhuma equivalência encontrada para 1101"
        codigos = {e["codigo_fabricante"] for e in equivs}
        # SM deve sempre estar presente (dados inline)
        assert "1101SG" in codigos, f"1101SG não encontrado nas equivalências: {codigos}"

    def test_equivalencia_1101_sm_he_al(self):
        """Com JSONs carregados, todas as 3 marcas devem aparecer."""
        equivs = buscar_equivalentes("1101")
        codigos = {e["codigo_fabricante"] for e in equivs}
        # SM sempre presente
        assert "1101SG" in codigos

    def test_equivalencia_1520_fechadura(self):
        """Fechadura 1520 deve ter equivalência em SM."""
        equivs = buscar_equivalentes("1520")
        codigos = {e["codigo_fabricante"] for e in equivs}
        assert "1520G" in codigos, f"1520G não encontrado: {codigos}"

    def test_busca_codigo_normalizado(self):
        """Buscar '1101' deve retornar ferragem do SM."""
        ferr = buscar_ferragem("1101")
        assert ferr is not None, "Nenhuma ferragem encontrada para código '1101'"

    def test_busca_codigo_completo_sm(self):
        """Buscar '1101SG' deve retornar a ferragem exata do SM."""
        ferr = buscar_ferragem("1101SG")
        assert ferr is not None, "Ferragem 1101SG não encontrada"
        assert "dobra" in ferr["tipo"].lower() or "dobradica" in ferr["tipo"], (
            f"Tipo inesperado: {ferr['tipo']}"
        )


class TestRecortes:
    def test_recorte_1101_onda(self):
        """Recorte da 1101SG deve ser tipo onda, 110mm comprimento, furo 25mm."""
        recortes = buscar_recortes("1101SG")
        assert len(recortes) >= 1, "Nenhum recorte para 1101SG"
        r = recortes[0]
        assert r["tipo"] == "onda", f"Tipo esperado 'onda', encontrado: {r['tipo']}"
        assert r["comprimento_mm"] == 110, f"Comprimento esperado 110, encontrado: {r['comprimento_mm']}"
        assert r["furo_diametro_mm"] == 25, f"Furo esperado 25, encontrado: {r['furo_diametro_mm']}"

    def test_recorte_1103_onda(self):
        """Recorte da 1103SG: 125mm comprimento, furo 25mm."""
        recortes = buscar_recortes("1103SG")
        assert len(recortes) >= 1, "Nenhum recorte para 1103SG"
        r = recortes[0]
        assert r["comprimento_mm"] == 125, f"Comprimento esperado 125, encontrado: {r['comprimento_mm']}"
        assert r["furo_diametro_mm"] == 25

    def test_fechadura_1520_recorte(self):
        """Fechadura 1520G recorte: 73x45mm R8 (Glasspeças)."""
        recortes = buscar_recortes("1520G")
        assert len(recortes) >= 1, "Nenhum recorte para 1520G"
        r = recortes[0]
        assert r["comprimento_mm"] == 73, f"Comprimento esperado 73, encontrado: {r['comprimento_mm']}"
        assert r["largura_mm"] == 45, f"Largura esperada 45, encontrada: {r['largura_mm']}"
        assert r["raio_mm"] == 8, f"Raio esperado 8, encontrado: {r['raio_mm']}"


class TestTotais:
    def test_total_ferragens_minimo(self):
        """Deve ter pelo menos as ferragens do SM (7 inline)."""
        stats = get_stats()
        assert stats["ferragens"] >= 7, (
            f"Esperado >= 7 ferragens (SM inline), encontrado: {stats['ferragens']}"
        )

    def test_total_kits_minimo(self):
        """Deve ter pelo menos 1 kit (SM inline)."""
        stats = get_stats()
        assert stats["kits"] >= 1, (
            f"Esperado >= 1 kit, encontrado: {stats['kits']}"
        )

    def test_total_ferragens_com_json(self):
        """Com JSONs de HE e AL, deve ter >= 150 ferragens."""
        from tools.catalog_loader import HELA_JSON, AL_JSON
        stats = get_stats()
        if HELA_JSON.exists() and AL_JSON.exists():
            assert stats["ferragens"] >= 150, (
                f"Com HE + AL + SM, esperado >= 150 ferragens, encontrado: {stats['ferragens']}"
            )

    def test_total_kits_com_json(self):
        """Com JSONs carregados, deve ter >= 47 kits (35 HE + 12 AL + SM)."""
        from tools.catalog_loader import HELA_JSON, AL_JSON
        stats = get_stats()
        if HELA_JSON.exists() and AL_JSON.exists():
            assert stats["kits"] >= 47, (
                f"Com HE + AL + SM, esperado >= 47 kits, encontrado: {stats['kits']}"
            )

    def test_folgas_nbr_populadas(self):
        """Folgas NBR devem estar populadas (movel_fixo=3, movel_piso=8, etc)."""
        stats = get_stats()
        assert stats["folgas_nbr"] >= 5, (
            f"Esperado >= 5 folgas NBR, encontrado: {stats['folgas_nbr']}"
        )


class TestIdempotencia:
    def test_idempotencia(self):
        """Rodar catalog_loader 2x não deve duplicar registros."""
        stats_antes = get_stats()

        with CatalogLoader(dry_run=False) as loader:
            loader.carregar_glasspecas()

        stats_depois = get_stats()

        assert stats_depois["ferragens"] == stats_antes["ferragens"], (
            f"Ferragens duplicadas! Antes={stats_antes['ferragens']}, "
            f"Depois={stats_depois['ferragens']}"
        )
        assert stats_depois["kits"] == stats_antes["kits"], (
            f"Kits duplicados! Antes={stats_antes['kits']}, Depois={stats_depois['kits']}"
        )


class TestFormulas:
    def test_formula_basculante(self):
        """Fórmula basculante deve existir na Constitution."""
        from app.core.constitution import _get_conn
        conn = _get_conn()
        row = conn.execute(
            "SELECT * FROM formulas WHERE nome LIKE '%basculante%'"
        ).fetchone()
        conn.close()
        assert row is not None, "Fórmula basculante não encontrada na Constitution"
        assert "48000" in row["formula"], (
            f"Fórmula inesperada: {row['formula']}"
        )

    def test_folga_movel_fixo(self):
        """Folga movel_fixo deve ser 3mm."""
        from app.core.constitution import _get_conn
        conn = _get_conn()
        row = conn.execute(
            "SELECT valor_mm FROM folgas_nbr WHERE tipo='movel_fixo'"
        ).fetchone()
        conn.close()
        assert row is not None, "Folga movel_fixo não encontrada"
        assert row["valor_mm"] == 3.0, f"Esperado 3mm, encontrado: {row['valor_mm']}"

    def test_folga_movel_piso(self):
        """Folga movel_piso deve ser 8mm."""
        from app.core.constitution import _get_conn
        conn = _get_conn()
        row = conn.execute(
            "SELECT valor_mm FROM folgas_nbr WHERE tipo='movel_piso'"
        ).fetchone()
        conn.close()
        assert row is not None, "Folga movel_piso não encontrada"
        assert row["valor_mm"] == 8.0, f"Esperado 8mm, encontrado: {row['valor_mm']}"


# ─── CORREÇÃO 1: Fórmulas — normalização canônica ─────────────────────────────

class TestNormalizarFormula:
    def test_largura_maiuscula(self):
        assert normalizar_formula("LARGURA / 2") == "largura / 2"

    def test_altura_maiuscula(self):
        assert normalizar_formula("ALTURA - 50") == "altura - 50"

    def test_formula_mista(self):
        assert normalizar_formula("(48000 / LARGURA + ALTURA) / 2") == \
               "(48000 / largura + altura) / 2"

    def test_formula_ja_minuscula(self):
        """Fórmula já normalizada não muda — idempotente."""
        f = "altura * 0.50"
        assert normalizar_formula(f) == f

    def test_aplica_n_vezes(self):
        """Aplicar N vezes dá o mesmo resultado — idempotente."""
        f = "LARGURA - 50"
        r1 = normalizar_formula(f)
        r2 = normalizar_formula(r1)
        assert r1 == r2


class TestFormulasNoDb:
    def test_zero_formulas_com_variaveis_maiusculas(self):
        """Nenhuma fórmula no DB deve ter variáveis em maiúsculas.
        Usa GLOB (case-sensitive) pois SQLite LIKE é case-insensitive por padrão."""
        conn = sqlite3.connect(str(DB_PATH))
        # GLOB é case-sensitive no SQLite — garante que não há maiúsculas
        rows = conn.execute(
            "SELECT nome, formula FROM formulas "
            "WHERE formula GLOB '*LARGURA*' OR formula GLOB '*ALTURA*' "
            "   OR formula GLOB '*COMPRIMENTO*' OR formula GLOB '*ESPESSURA*' "
            "   OR formula GLOB '*VANO_L*' OR formula GLOB '*VANO_H*'"
        ).fetchall()
        conn.close()
        assert len(rows) == 0, (
            f"Fórmulas com variáveis maiúsculas encontradas: "
            + ", ".join(f"'{nome}': {formula}" for nome, formula in rows)
        )

    def test_formula_basculante_minuscula(self):
        """Fórmula basculante deve usar variáveis minúsculas e conter 48000."""
        conn = sqlite3.connect(str(DB_PATH))
        row = conn.execute(
            "SELECT formula FROM formulas WHERE nome LIKE '%basculante%'"
        ).fetchone()
        conn.close()
        assert row is not None, "Fórmula basculante não encontrada"
        formula = row[0]
        assert "48000" in formula, f"Número mágico 48000 ausente: {formula}"
        assert "largura" in formula, f"'largura' (minúsculo) ausente: {formula}"
        assert "altura" in formula, f"'altura' (minúsculo) ausente: {formula}"
        assert "LARGURA" not in formula, f"'LARGURA' (maiúsculo) ainda presente: {formula}"


class TestEvalFormula:
    def test_formula_simples(self):
        """_eval_formula deve retornar valor correto para fórmula simples."""
        from app.services.constitution_engine import _eval_formula
        assert _eval_formula("largura / 2", 900, 2100) == 450.0

    def test_formula_basculante(self):
        """Fórmula basculante: ~334 para largura=700, altura=600."""
        from app.services.constitution_engine import _eval_formula
        result = _eval_formula("(48000 / largura + altura) / 2", 700, 600)
        assert 330 < result < 340, f"Basculante 700×600 deveria ser ~334, foi {result}"

    def test_formula_maiuscula_aceita(self):
        """Engine aceita fórmula com maiúsculas via normalizar_formula defensivo."""
        from app.services.constitution_engine import _eval_formula
        assert _eval_formula("LARGURA / 2", 900, 2100) == 450.0

    def test_formula_invalida_levanta_excecao(self):
        """Fórmula inválida deve levantar ValueError, não retornar 0.0 silenciosamente."""
        from app.services.constitution_engine import _eval_formula
        with pytest.raises((ValueError, Exception)):
            _eval_formula("variavel_inexistente / 2", 900, 2100)


# ─── CORREÇÃO 2: Recortes AL — tipo inferido ──────────────────────────────────

class TestInferirTipoRecorte:
    def test_so_furo(self):
        assert inferir_tipo_recorte(None, None, 12, None) == "furo_passante"

    def test_furo_comp_larg(self):
        """Comp + larg + furo (sem raio) = onda (dobradiça)."""
        assert inferir_tipo_recorte(110, 27, 25, None) == "onda"

    def test_comp_larg_furo_raio(self):
        """Comp + larg + furo + raio = retangular_arredondado (fechadura)."""
        assert inferir_tipo_recorte(76, 40, 16, 7) == "retangular_arredondado"

    def test_comp_larg_raio_sem_furo(self):
        assert inferir_tipo_recorte(73, 45, None, 8) == "retangular_arredondado"

    def test_comp_larg_sem_furo_raio(self):
        assert inferir_tipo_recorte(50, 27, None, None) == "retangular"

    def test_fallback_por_nome_dobradica(self):
        assert inferir_tipo_recorte(None, None, None, None, "dobradiça superior") == "onda"

    def test_fallback_por_nome_puxador(self):
        assert inferir_tipo_recorte(None, None, None, None, "puxador botão") == "furo_passante"

    def test_default(self):
        """Sem dados, retorna furo_passante (mais seguro para SVG)."""
        assert inferir_tipo_recorte(None, None, None, None) == "furo_passante"


class TestZeroRecortesSemTipo:
    def test_zero_recortes_tipo_null(self):
        """Nenhum recorte no DB deve ter tipo NULL após o loader."""
        conn = sqlite3.connect(str(DB_PATH))
        sem_tipo = conn.execute(
            "SELECT COUNT(*) FROM recortes WHERE tipo IS NULL"
        ).fetchone()[0]
        conn.close()
        assert sem_tipo == 0, f"{sem_tipo} recortes com tipo=NULL no DB"

    def test_tipos_recorte_validos(self):
        """Todos os tipos de recorte devem ser de um conjunto conhecido."""
        TIPOS_VALIDOS = {
            "furo_passante", "onda", "retangular",
            "retangular_arredondado", "chanfro", "reto", "especial",
        }
        conn = sqlite3.connect(str(DB_PATH))
        tipos = conn.execute(
            "SELECT DISTINCT tipo FROM recortes WHERE tipo IS NOT NULL"
        ).fetchall()
        conn.close()
        for (tipo,) in tipos:
            assert tipo in TIPOS_VALIDOS, (
                f"Tipo desconhecido no DB: '{tipo}'. "
                f"Adicionar a TIPOS_VALIDOS se for válido."
            )


# ─── CORREÇÃO 3: AL 1335 multi-contexto ──────────────────────────────────────

class TestMultiContextoParser:
    def test_detecta_multi_contexto(self):
        raw = {
            "p_janela": {"furo_diametro": 25, "comprimento": 50},
            "p_porta":  {"furo_diametro": 18, "comprimento": 45, "largura": 25},
        }
        assert _is_multi_context_recorte(raw) is True

    def test_nao_detecta_single(self):
        raw = {"comprimento": 110, "largura": 27, "furo_diametro": 25}
        assert _is_multi_context_recorte(raw) is False

    def test_parse_extrai_dois_contextos(self):
        raw = {
            "p_janela": {"furo_diametro": 25, "comprimento": 50},
            "p_porta":  {"furo_diametro": 18, "comprimento": 45, "largura": 25},
        }
        resultado = parse_recorte_multi_contexto(raw)
        assert len(resultado) == 2
        contextos = {r["contexto"] for r in resultado}
        assert "janela" in contextos
        assert "porta" in contextos

    def test_parse_dimensoes_corretas(self):
        raw = {
            "p_janela": {"furo_diametro": 25, "comprimento": 50},
            "p_porta":  {"furo_diametro": 18, "comprimento": 45, "largura": 25},
        }
        por_ctx = {r["contexto"]: r for r in parse_recorte_multi_contexto(raw)}
        assert por_ctx["janela"]["furo_mm"] == 25
        assert por_ctx["janela"]["comp_mm"] == 50
        assert por_ctx["porta"]["comp_mm"] == 45
        assert por_ctx["porta"]["larg_mm"] == 25


class TestAL1335NoDB:
    def test_al_1335_tem_dois_contextos(self):
        """AL 1335 deve ter 2 recortes (janela e porta) no DB."""
        from tools.catalog_loader import HELA_JSON, AL_JSON
        if not AL_JSON.exists():
            pytest.skip("catalogo_al_industria.json não disponível")
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute(
            "SELECT contexto_aplicacao, comprimento_mm, furo_diametro_mm "
            "FROM recortes WHERE ferragem_codigo='AL 1335'"
        ).fetchall()
        conn.close()
        assert len(rows) >= 2, (
            f"AL 1335 deveria ter >=2 recortes (um por contexto), encontrado: {len(rows)}"
        )
        contextos = {r[0] for r in rows}
        assert "janela" in contextos or "porta" in contextos, (
            f"Contextos esperados: janela/porta. Encontrados: {contextos}"
        )

    def test_coluna_contexto_existe(self):
        """Tabela recortes deve ter coluna contexto_aplicacao."""
        conn = sqlite3.connect(str(DB_PATH))
        info = conn.execute("PRAGMA table_info(recortes)").fetchall()
        conn.close()
        colunas = {row[1] for row in info}
        assert "contexto_aplicacao" in colunas, (
            f"Coluna contexto_aplicacao não encontrada. Colunas: {colunas}"
        )


# ─── CORREÇÃO 4: Folgas NBR — interface de consulta ──────────────────────────

class TestFolgasNBRInterface:
    def test_todas_folgas_retorna_dict(self):
        folgas = todas_folgas_nbr()
        assert isinstance(folgas, dict)
        assert len(folgas) >= 5, f"Esperado >=5 folgas, encontrado: {len(folgas)}"

    def test_valores_razoaveis(self):
        """Todas as folgas devem estar entre 0 e 15mm."""
        folgas = todas_folgas_nbr()
        for tipo, valor in folgas.items():
            assert 0 < valor <= 15, (
                f"Folga '{tipo}' = {valor}mm fora do range esperado (0–15mm)"
            )

    def test_buscar_folga_movel_fixo(self):
        val = buscar_folga_nbr("movel_fixo")
        assert val is not None, "movel_fixo não encontrado no DB"
        assert val == 3.0, f"Esperado 3.0mm, encontrado: {val}"

    def test_buscar_folga_movel_piso(self):
        val = buscar_folga_nbr("movel_piso")
        assert val is not None, "movel_piso não encontrado no DB"
        assert val == 8.0, f"Esperado 8.0mm, encontrado: {val}"

    def test_buscar_folga_inexistente_retorna_none(self):
        assert buscar_folga_nbr("tipo_que_nao_existe") is None


# ─── CORREÇÃO 5: Artefatos + prevenção ───────────────────────────────────────

class TestArtefatosLimpos:
    def test_escada_rolante_removida(self):
        """escada_rolante não deve existir na Constitution."""
        conn = sqlite3.connect(str(DB_PATH))
        count = conn.execute(
            "SELECT COUNT(*) FROM constitution_entries WHERE chave='escada_rolante'"
        ).fetchone()[0]
        conn.close()
        assert count == 0, f"escada_rolante ainda no DB ({count} registro(s))"

    def test_tipologia_inexistente_removida(self):
        """tipologia_inexistente_xyz não deve existir na Constitution."""
        conn = sqlite3.connect(str(DB_PATH))
        count = conn.execute(
            "SELECT COUNT(*) FROM constitution_entries WHERE chave='tipologia_inexistente_xyz'"
        ).fetchone()[0]
        conn.close()
        assert count == 0, f"tipologia_inexistente_xyz ainda no DB ({count} registro(s))"


class TestBlacklistTipologia:
    def test_rejeita_escada(self):
        from app.services.claude_teacher import _tipologia_valida
        assert _tipologia_valida("escada_rolante") is False

    def test_rejeita_teste(self):
        from app.services.claude_teacher import _tipologia_valida
        assert _tipologia_valida("teste_xyz") is False

    def test_aceita_porta_pivotante(self):
        from app.services.claude_teacher import _tipologia_valida
        assert _tipologia_valida("porta_pivotante_simples") is True

    def test_aceita_box_banheiro(self):
        from app.services.claude_teacher import _tipologia_valida
        assert _tipologia_valida("box_banheiro") is True

    def test_aceita_janela_maxim_ar(self):
        from app.services.claude_teacher import _tipologia_valida
        assert _tipologia_valida("janela_maxim_ar") is True
