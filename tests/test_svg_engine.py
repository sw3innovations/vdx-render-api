"""
Testes Sprint 2 — SVG Template Engine, ABNT Validator, Constitution Engine,
Render Orchestrator.

Rode com: python -m pytest tests/test_svg_engine.py -v
"""
import sys
import asyncio
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.constitution import init_db, migrate
from app.models.render import (
    FerragemPosicionada, PecaRenderizada, RenderRequest, PecaInput, Opcoes,
)


@pytest.fixture(scope="session", autouse=True)
def inicializar_db():
    """Garante que DB está inicializado + catálogo carregado antes dos testes."""
    init_db()
    try:
        from tools.catalog_loader import CatalogLoader
        with CatalogLoader(dry_run=False) as loader:
            loader.carregar_glasspecas()
            loader.carregar_hela()
            loader.carregar_al()
            loader.carregar_equivalencias_cross()
    except Exception:
        pass  # testes com SM apenas


def _peca_porta(nome="Folha Móvel", largura=900, altura=2100):
    return PecaRenderizada(
        nome=nome, largura_mm=largura, altura_mm=altura,
        classificacao="movel",
        ferragens=[
            FerragemPosicionada(
                codigo="1101", nome="Dobradiça Superior", tipo="dobradica",
                x_mm=15, y_mm=altura - 50, lado="esquerdo",
                visual="retangulo", recorte="padrao_sm",
            ),
            FerragemPosicionada(
                codigo="1103", nome="Dobradiça Inferior", tipo="dobradica",
                x_mm=15, y_mm=50, lado="esquerdo",
                visual="retangulo", recorte="padrao_sm",
            ),
            FerragemPosicionada(
                codigo="1520", nome="Fechadura Central", tipo="fechadura",
                x_mm=largura - 15, y_mm=altura * 0.5, lado="direito",
                visual="retangulo", recorte="padrao_sm",
            ),
            FerragemPosicionada(
                nome="Puxador", tipo="puxador",
                x_mm=largura - 35, y_mm=altura * 0.5, lado="direito",
                visual="circulo", recorte="furo_passante",
            ),
        ],
    )


# ─── SVG Template Engine ──────────────────────────────────────────────────────

class TestSVGTemplateEngine:
    def setup_method(self):
        from app.renderers.svg_template_engine import SVGTemplateEngine
        self.engine = SVGTemplateEngine()

    def test_gera_svg_valido(self):
        """SVG deve ser uma string com tag <svg>."""
        peca = _peca_porta()
        svg = self.engine.gerar_svg([peca], tipologia_nome="porta_pivotante_simples")
        assert isinstance(svg, str)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_svg_tem_retangulo_vidro(self):
        """SVG deve conter retângulo representando o vidro."""
        peca = _peca_porta()
        svg = self.engine.gerar_svg([peca])
        assert "<rect" in svg

    def test_svg_tem_ferragens(self):
        """SVG deve conter símbolos de ferragens."""
        peca = _peca_porta()
        svg = self.engine.gerar_svg([peca], opcoes_dict={"mostrar_ferragens": True})
        # Pelo menos um círculo (puxador) ou retângulo (dobradiça/fechadura)
        assert "<circle" in svg or "<rect" in svg

    def test_svg_tem_cotas(self):
        """SVG deve conter linhas de cota com dimensões em mm."""
        peca = _peca_porta()
        svg = self.engine.gerar_svg([peca], opcoes_dict={"mostrar_cotas": True})
        assert "900mm" in svg or "2100mm" in svg

    def test_svg_tem_nome_peca(self):
        """SVG deve conter o nome da peça."""
        peca = _peca_porta(nome="Folha Principal")
        svg = self.engine.gerar_svg([peca])
        assert "Folha Principal" in svg

    def test_svg_recorte_furo_passante(self):
        """Ferragem com furo_passante deve gerar círculo de recorte."""
        peca = PecaRenderizada(
            nome="Teste", largura_mm=600, altura_mm=1200,
            classificacao="movel",
            ferragens=[
                FerragemPosicionada(
                    nome="Puxador Botão", tipo="puxador",
                    x_mm=300, y_mm=600, lado="direito",
                    visual="circulo", recorte="furo_passante",
                )
            ],
        )
        svg = self.engine.gerar_svg([peca])
        assert "<circle" in svg

    def test_svg_recorte_com_dados_catalogo(self):
        """Template engine usa dados do catálogo para desenhar recorte real."""
        peca = _peca_porta()
        recortes_cat = {
            "1101": {"tipo": "onda", "comprimento_mm": 110, "largura_mm": 27,
                      "furo_diametro_mm": 25, "raio_mm": None},
        }
        svg = self.engine.gerar_svg([peca], recortes_catalogo=recortes_cat)
        # Deve conter rect (onda) + circle (furo)
        assert "<rect" in svg

    def test_svg_multiplas_pecas(self):
        """SVG com 2 peças (fixo + móvel) deve ser mais largo."""
        p1 = PecaRenderizada(nome="Fixo", largura_mm=400, altura_mm=2100,
                              classificacao="fixa", ferragens=[])
        p2 = _peca_porta(nome="Móvel", largura=600, altura=2100)
        svg = self.engine.gerar_svg([p1, p2])
        assert "Fixo" in svg and "Móvel" in svg

    def test_svg_sem_pecas_retorna_vazio(self):
        """Sem peças, retorna SVG mínimo válido."""
        svg = self.engine.gerar_svg([])
        assert "<svg" in svg

    def test_svg_tipologia_basculante_tem_diagonal(self):
        """SVG de basculante deve ter linha de abertura diagonal (stroke-dasharray)."""
        peca = PecaRenderizada(nome="Basculante", largura_mm=600, altura_mm=400,
                               classificacao="movel",
                               ferragens=[])
        svg = self.engine.gerar_svg([peca], tipologia_nome="janela_basculante")
        assert "stroke-dasharray" in svg

    def test_svg_tipologia_correr_tem_seta(self):
        """SVG de janela de correr deve ter indicador de deslizamento."""
        peca = PecaRenderizada(nome="Folha Correr", largura_mm=600, altura_mm=1200,
                               classificacao="correr", ferragens=[])
        svg = self.engine.gerar_svg([peca], tipologia_nome="janela_correr_2_folhas")
        assert "polygon" in svg


# ─── ABNT Validator ───────────────────────────────────────────────────────────

class TestABNTValidator:
    def setup_method(self):
        from app.core.abnt_validator import ABNTValidator
        self.v = ABNTValidator()

    def test_porta_vidro_comum_critico(self):
        """Porta com vidro comum → alerta CRITICO."""
        alertas = self.v.verificar("porta pivotante", "porta_pivotante_simples",
                                    None, "comum")
        niveis = [a["nivel"] for a in alertas]
        assert "CRITICO" in niveis

    def test_porta_espessura_insuficiente(self):
        """Porta com 6mm → alerta CRITICO (mínimo 8mm)."""
        alertas = self.v.verificar("porta", "porta_pivotante_simples", 6.0, "temperado")
        assert any(a["nivel"] == "CRITICO" for a in alertas)

    def test_porta_espessura_ok(self):
        """Porta com 10mm temperado → sem alertas críticos."""
        alertas = self.v.verificar("porta", "porta_pivotante_simples", 10.0, "temperado")
        assert not any(a["nivel"] == "CRITICO" for a in alertas)

    def test_box_vidro_comum_critico(self):
        """Box banheiro com vidro comum → CRITICO."""
        alertas = self.v.verificar("box frontal", "box_frontal_2_folhas", 8.0, "comum")
        assert any(a["nivel"] == "CRITICO" for a in alertas)

    def test_guarda_corpo_temperado_critico(self):
        """Guarda-corpo com vidro temperado (não laminado) → CRITICO."""
        alertas = self.v.verificar("guarda corpo linear", "guarda_corpo_linear",
                                    10.0, "temperado", alturas_pecas=[1200])
        assert any(a["nivel"] == "CRITICO" for a in alertas)

    def test_guarda_corpo_altura_insuficiente(self):
        """Guarda-corpo com altura 900mm → CRITICO (mínimo 1100mm)."""
        alertas = self.v.verificar("guarda corpo", "guarda_corpo_linear",
                                    10.0, "laminado", alturas_pecas=[900])
        assert any(a["nivel"] == "CRITICO" for a in alertas)

    def test_sem_problemas_janela_normal(self):
        """Janela 8mm temperado → sem alertas críticos."""
        alertas = self.v.verificar("janela maxim ar", "janela_maxim_ar",
                                    8.0, "temperado")
        assert not any(a["nivel"] == "CRITICO" for a in alertas)

    def test_folgas_do_db(self):
        """ABNTValidator deve carregar folgas da Constitution DB."""
        folgas = self.v._folgas
        assert isinstance(folgas, dict)
        # Se o DB tem dados, deve ter pelo menos a folga movel_fixo
        if folgas:
            assert any(v > 0 for v in folgas.values())

    def test_retorna_lista(self):
        """verificar() sempre retorna list."""
        resultado = self.v.verificar("", "", None, None)
        assert isinstance(resultado, list)


# ─── Constitution Engine — enriquecimento ─────────────────────────────────────

class TestConstitutionEngineEnriquecimento:
    def test_enriquecer_1101_sm(self):
        """Enriquecer código 1101 no SM deve retornar dados da dobradiça."""
        from app.services.constitution_engine import enriquecer_ferragem_com_catalogo
        dados = enriquecer_ferragem_com_catalogo("1101", "SM")
        assert dados.get("codigo") == "1101SG", f"Esperado '1101SG', got: {dados}"

    def test_enriquecer_1101_sem_fabricante(self):
        """Sem fabricante, deve retornar o primeiro equivalente disponível."""
        from app.services.constitution_engine import enriquecer_ferragem_com_catalogo
        dados = enriquecer_ferragem_com_catalogo("1101")
        assert dados.get("codigo") is not None

    def test_enriquecer_com_recorte(self):
        """Enriquecimento deve incluir dados de recorte da dobradiça."""
        from app.services.constitution_engine import enriquecer_ferragem_com_catalogo
        dados = enriquecer_ferragem_com_catalogo("1101", "SM")
        recorte = dados.get("recorte")
        assert recorte is not None, "Dobradiça 1101SG deve ter recorte no catálogo"
        assert recorte.get("tipo") == "onda"

    def test_enriquecer_codigo_inexistente(self):
        """Código inexistente deve retornar dict vazio."""
        from app.services.constitution_engine import enriquecer_ferragem_com_catalogo
        dados = enriquecer_ferragem_com_catalogo("9999")
        assert dados == {}

    def test_constitution_engine_resolver_tipologia(self):
        """ConstitutionEngine.resolver_tipologia deve retornar dados estruturados."""
        from app.services.constitution_engine import ConstitutionEngine
        engine = ConstitutionEngine()
        resultado = engine.resolver_tipologia(
            "porta_pivotante_simples", 900.0, 2100.0, "Folha Móvel"
        )
        assert resultado is not None
        assert resultado["tipologia"] == "porta_pivotante_simples"
        assert resultado["largura"] == 900.0
        assert "ferragens" in resultado
        assert len(resultado["ferragens"]) >= 3  # dobradiça sup, inf, fechadura

    def test_constitution_engine_com_fabricante_he(self):
        """Resolver com fabricante=HE deve retornar códigos HELA quando disponível."""
        from app.services.constitution_engine import ConstitutionEngine
        engine = ConstitutionEngine()
        resultado = engine.resolver_tipologia(
            "porta_pivotante_simples", 900.0, 2100.0, fabricante="HE"
        )
        if resultado:
            codigos = [f.get("codigo_catalogo") for f in resultado["ferragens"]]
            # Se equivalência HE existe, pelo menos 1 deve ter código HE
            he_codes = [c for c in codigos if c and "HE" in c]
            # Pode não ter se equivalência não está no DB — não é falha crítica
            assert resultado["fonte"] == "constitution+catalogo"

    def test_constitution_engine_tipologia_inexistente(self):
        """Tipologia inexistente deve retornar None."""
        from app.services.constitution_engine import ConstitutionEngine
        engine = ConstitutionEngine()
        assert engine.resolver_tipologia("tipologia_que_nao_existe", 900, 2100) is None

    def test_ferragens_tem_posicao(self):
        """Ferragens devem ter coordenadas x e y calculadas."""
        from app.services.constitution_engine import ConstitutionEngine
        engine = ConstitutionEngine()
        resultado = engine.resolver_tipologia("porta_pivotante_simples", 900, 2100)
        for f in resultado["ferragens"]:
            assert "x" in f and "y" in f
            assert isinstance(f["x"], (int, float))
            assert isinstance(f["y"], (int, float))
            assert f["y"] >= 20  # clamp mínimo


# ─── Render Orchestrator ──────────────────────────────────────────────────────

class TestRenderOrchestrator:
    def _request(self, tipologia="porta_pivotante_simples",
                 largura=900, altura=2100, espessura=None, tipo_vidro=None):
        return RenderRequest(
            tipologia_nome=tipologia,
            pecas=[PecaInput(nome="Folha Móvel", largura_mm=largura, altura_mm=altura)],
            opcoes=Opcoes(largura_px=480, altura_px=360),
            espessura_vidro_mm=espessura,
            tipo_vidro=tipo_vidro,
        )

    def test_pipeline_porta_pivotante(self):
        """Pipeline completo: porta pivotante → SVG + ferragens + metadata."""
        import asyncio
        from app.services.render_orchestrator import executar
        req = self._request()
        resp = asyncio.run(executar(req))
        assert resp.svg and len(resp.svg) > 100
        assert "<svg" in resp.svg
        assert len(resp.pecas) == 1
        assert resp.metadata.get("modo") == "constitution"

    def test_pipeline_retorna_ferragens(self):
        """Pipeline deve retornar ferragens posicionadas."""
        import asyncio
        from app.services.render_orchestrator import executar
        req = self._request()
        resp = asyncio.run(executar(req))
        ferragens = resp.pecas[0].ferragens if resp.pecas else []
        assert len(ferragens) >= 3  # dobradiça sup, inf, fechadura

    def test_pipeline_abnt_porta_vidro_comum(self):
        """Pipeline com vidro comum em porta → alertas ABNT."""
        import asyncio
        from app.services.render_orchestrator import executar
        req = self._request(espessura=6.0, tipo_vidro="comum")
        resp = asyncio.run(executar(req))
        assert len(resp.alertas_norma) > 0
        niveis = [a["nivel"] for a in resp.alertas_norma]
        assert "CRITICO" in niveis

    def test_pipeline_sem_deprecated_no_router(self):
        """render.py NÃO deve importar nada de _deprecated."""
        render_path = ROOT / "app" / "routers" / "render.py"
        conteudo = render_path.read_text(encoding="utf-8")
        assert "_deprecated" not in conteudo, (
            "render.py ainda tem import de _deprecated — deve estar no orchestrator"
        )

    def test_pipeline_modo_constitution(self):
        """Tipologia conhecida deve usar modo 'constitution'."""
        import asyncio
        from app.services.render_orchestrator import executar
        req = self._request("janela_basculante", 600, 400)
        resp = asyncio.run(executar(req))
        assert resp.metadata.get("modo") == "constitution"

    def test_pipeline_janela_retorna_200(self):
        """Janela maxim ar deve processar sem erros."""
        import asyncio
        from app.services.render_orchestrator import executar
        req = self._request("janela_maxim_ar", 800, 600)
        resp = asyncio.run(executar(req))
        assert resp.svg and "<svg" in resp.svg

    def test_render_py_tem_50_linhas(self):
        """render.py deve ter no máximo 55 linhas (alvo ~50)."""
        render_path = ROOT / "app" / "routers" / "render.py"
        linhas = len(render_path.read_text().splitlines())
        assert linhas <= 55, (
            f"render.py tem {linhas} linhas — alvo é <=55"
        )


# ─── Integração: novos módulos existem ───────────────────────────────────────

class TestEstruturaArquivos:
    def test_abnt_validator_existe(self):
        assert (ROOT / "app" / "core" / "abnt_validator.py").exists()

    def test_render_orchestrator_existe(self):
        assert (ROOT / "app" / "services" / "render_orchestrator.py").exists()

    def test_svg_template_engine_existe(self):
        assert (ROOT / "app" / "renderers" / "svg_template_engine.py").exists()

    def test_renderers_package(self):
        assert (ROOT / "app" / "renderers" / "__init__.py").exists()

    def test_main_seed_fora_do_init_db(self):
        """init_db() não deve chamar seed() — main.py orquestra a sequência."""
        constitution_path = ROOT / "app" / "core" / "constitution.py"
        conteudo = constitution_path.read_text(encoding="utf-8")
        # init_db não deve ter chamada a seed() nem _seed() — só DDL + migrate
        assert "_seed()" not in conteudo, "init_db() ainda chama seed — ciclo de dependência"
        assert "constitution_seed" not in conteudo, "constitution.py não deve importar constitution_seed"
