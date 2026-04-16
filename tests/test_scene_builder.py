"""
Testes do Sprint 4: SceneBuilder + endpoints 3D.
"""
import asyncio
import json
import pytest

from app.core.constitution import init_db
from app.core.constitution_seed import seed
from app.models.render import PecaInput, RenderRequest
from app.renderers.scene_builder import SceneBuilder, CORES_VIDRO, MATERIAIS_PBR
from app.services.render_orchestrator import executar


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()
    seed()


def _render(tipologia: str, pecas: list[PecaInput] | None = None) -> object:
    if pecas is None:
        pecas = [PecaInput(nome="Porta", largura_mm=900, altura_mm=2100)]
    req = RenderRequest(tipologia_nome=tipologia, pecas=pecas)
    return asyncio.run(executar(req))


def _scene(tipologia: str, pecas=None, cor_vidro="default", espessura=8.0):
    resp = _render(tipologia, pecas)
    return SceneBuilder().build(resp, espessura_vidro=espessura, cor_vidro=cor_vidro)


# ── Task 6.1: Schema obrigatório ──────────────────────────────────────────────

class TestSchemaObrigatorio:
    def test_campos_top_level(self):
        s = _scene("porta_pivotante_simples")
        assert s["version"] in ("1.0", "2.0")
        assert s["unidade"] == "mm"
        for campo in ("tipologia", "dimensoes", "vidros", "ferragens", "vao", "ambiente"):
            assert campo in s, f"Campo '{campo}' ausente"

    def test_dimensoes(self):
        s = _scene("porta_pivotante_simples")
        d = s["dimensoes"]
        assert d["largura"] == 900.0
        assert d["altura"]  == 2100.0
        assert d["espessura_vidro"] == 8.0

    def test_vao_maior_que_vidro(self):
        s = _scene("porta_pivotante_simples")
        assert s["vao"]["largura"] > s["dimensoes"]["largura"]
        assert s["vao"]["altura"]  > s["dimensoes"]["altura"]

    def test_camera_em_frente(self):
        s = _scene("porta_pivotante_simples")
        cam = s["ambiente"]["camera_inicial"]
        assert cam["posicao"]["z"] > 0, "Câmera deve estar em z > 0"
        assert cam["posicao"]["y"] > 0, "Câmera deve estar em y > 0"

    def test_json_size(self):
        """Scene JSON deve ser < 50 KB."""
        s = _scene("porta_pivotante_simples")
        size = len(json.dumps(s))
        assert size < 50_000, f"Scene JSON grande demais: {size} bytes"


# ── Task 6.2: Vidros ──────────────────────────────────────────────────────────

class TestVidros:
    def test_porta_simples_1_vidro(self):
        s = _scene("porta_pivotante_simples")
        assert len(s["vidros"]) == 1

    def test_porta_correr_2_vidros(self):
        s = _scene("porta_correr_2_folhas", [
            PecaInput(nome="Folha 1", largura_mm=450, altura_mm=2100),
            PecaInput(nome="Folha 2", largura_mm=450, altura_mm=2100),
        ])
        assert len(s["vidros"]) == 2

    def test_bandeira_dupla_2_vidros(self):
        s = _scene("porta_pivotante_dupla_bandeira", [
            PecaInput(nome="Bandeira", largura_mm=900, altura_mm=300),
            PecaInput(nome="Porta",    largura_mm=900, altura_mm=2100),
        ])
        assert len(s["vidros"]) == 2

    def test_vidro_material_ior(self):
        s = _scene("porta_pivotante_simples")
        mat = s["vidros"][0]["material"]
        assert mat["ior"] == 1.52
        assert 0.0 < mat["opacidade"] < 1.0
        assert 0.0 <= mat["roughness"] <= 0.1  # vidro: roughness baixo (0.0 ideal ou 0.05)

    def test_vidro_tem_classificacao(self):
        s = _scene("porta_pivotante_simples")
        v = s["vidros"][0]
        assert "classificacao" in v
        assert v["classificacao"] in ("movel", "fixa", "correr")

    def test_vidros_centrados_em_zero(self):
        """Para 1 vidro, centro X deve ser 0."""
        s = _scene("porta_pivotante_simples")
        v = s["vidros"][0]
        assert v["posicao"]["x"] == pytest.approx(0.0), "Vidro único deve estar em x=0"

    def test_vidros_2_folhas_simetricos(self):
        """2 folhas simétricas devem ter x's opostos."""
        s = _scene("porta_correr_2_folhas", [
            PecaInput(nome="Folha 1", largura_mm=450, altura_mm=2100),
            PecaInput(nome="Folha 2", largura_mm=450, altura_mm=2100),
        ])
        x0 = s["vidros"][0]["posicao"]["x"]
        x1 = s["vidros"][1]["posicao"]["x"]
        assert abs(x0 + x1) < 1.0, f"Vidros não simétricos: {x0}, {x1}"


# ── Task 6.3: Animações ───────────────────────────────────────────────────────

class TestAnimacoes:
    def test_pivotante(self):
        s = _scene("porta_pivotante_simples")
        moveis = [v for v in s["vidros"] if v.get("classificacao") == "movel"]
        assert len(moveis) == 1
        a = moveis[0]["animacao"]
        assert a["tipo"] == "pivotante"
        assert a["eixo"] == "y"
        assert a["angulo_max"] == 90

    def test_pivotante_tem_ponto_pivo(self):
        s = _scene("porta_pivotante_simples")
        moveis = [v for v in s["vidros"] if "animacao" in v]
        assert len(moveis) >= 1
        assert "ponto_pivo" in moveis[0]["animacao"]

    def test_correr_deslizante(self):
        s = _scene("porta_correr_2_folhas", [
            PecaInput(nome="Folha 1", largura_mm=450, altura_mm=2100),
            PecaInput(nome="Folha 2", largura_mm=450, altura_mm=2100),
        ])
        correr = [v for v in s["vidros"] if "animacao" in v]
        assert len(correr) >= 1
        assert correr[0]["animacao"]["tipo"] == "deslizante"
        assert correr[0]["animacao"]["eixo"] == "x"

    def test_basculante(self):
        s = _scene("janela_basculante", [
            PecaInput(nome="Basculante", largura_mm=800, altura_mm=400),
        ])
        moveis = [v for v in s["vidros"] if "animacao" in v]
        assert len(moveis) >= 1
        assert moveis[0]["animacao"]["tipo"] == "basculante"
        assert moveis[0]["animacao"]["eixo"] == "x"

    def test_fixa_sem_animacao(self):
        """Peças fixas NÃO devem ter campo animacao."""
        s = _scene("porta_pivotante_simples")
        fixas = [v for v in s["vidros"] if v.get("classificacao") == "fixa"]
        for v in fixas:
            assert "animacao" not in v, f"Peça fixa '{v['nome']}' tem animação"


# ── Task 6.4: Ferragens 3D ────────────────────────────────────────────────────

class TestFerragens3D:
    def test_posicao_3d_presente(self):
        s = _scene("porta_pivotante_simples")
        assert len(s["ferragens"]) >= 1
        for f in s["ferragens"]:
            pos = f["posicao"]
            assert "x" in pos and "y" in pos and "z" in pos

    def test_y_positivo(self):
        """y_mm do Constitution é da base → y_3d deve ser > 0."""
        s = _scene("porta_pivotante_simples")
        for f in s["ferragens"]:
            assert f["posicao"]["y"] > 0, f"Ferragem '{f['nome']}' tem y_3d ≤ 0"

    def test_z_nao_zero(self):
        """Ferragens devem ter z ≠ 0 (estão na face do vidro)."""
        s = _scene("porta_pivotante_simples")
        for f in s["ferragens"]:
            assert f["posicao"]["z"] != 0.0, f"Ferragem '{f['nome']}' está em z=0 (dentro do vidro)"

    def test_material_cromado_pivo(self):
        s = _scene("porta_pivotante_simples")
        pivos = [f for f in s["ferragens"] if f["tipo"] == "pivo"]
        assert len(pivos) >= 2, f"Esperava >= 2 pivôs, obteve: {[f['tipo'] for f in s['ferragens']]}"
        mat = pivos[0]["material"]
        assert mat["metalness"] >= 0.9, f"Pivô metalness baixo: {mat['metalness']}"
        assert mat["roughness"] <= 0.2, f"Pivô roughness alto: {mat['roughness']}"

    def test_geometria_presente(self):
        s = _scene("porta_pivotante_simples")
        for f in s["ferragens"]:
            assert "geometria" in f
            assert "tipo" in f["geometria"]
            assert f["geometria"]["tipo"] in ("box", "cylinder")

    def test_ids_unicos(self):
        s = _scene("box_banheiro", [
            PecaInput(nome="Fixo",  largura_mm=300, altura_mm=1900),
            PecaInput(nome="Porta", largura_mm=700, altura_mm=1900),
        ])
        ids = [f["id"] for f in s["ferragens"]]
        assert len(ids) == len(set(ids)), f"IDs duplicados: {ids}"


# ── Task 6.5: Cores de vidro ──────────────────────────────────────────────────

class TestCoresVidro:
    def test_cores_conhecidas(self):
        sb = SceneBuilder()
        for cor in CORES_VIDRO:
            resp = _render("porta_pivotante_simples")
            s = sb.build(resp, cor_vidro=cor)
            mat = s["vidros"][0]["material"]
            assert 0.0 < mat["opacidade"] <= 1.0, f"Cor '{cor}' opacidade inválida"

    def test_fume_mais_opaco_que_incolor(self):
        resp1 = _render("porta_pivotante_simples")
        resp2 = _render("porta_pivotante_simples")
        sb = SceneBuilder()
        s_fume   = sb.build(resp1, cor_vidro="fume")
        s_incolor = sb.build(resp2, cor_vidro="incolor")
        assert (s_fume["vidros"][0]["material"]["opacidade"] >
                s_incolor["vidros"][0]["material"]["opacidade"])

    def test_espelho_tem_metalness(self):
        resp = _render("porta_pivotante_simples")
        s = SceneBuilder().build(resp, cor_vidro="espelho")
        mat = s["vidros"][0]["material"]
        assert mat["metalness"] >= 0.7, "Espelho deve ter metalness alto"


# ── Task 6.6: Materiais PBR ───────────────────────────────────────────────────

class TestMateriaisPBR:
    def test_materiais_pbr_existem(self):
        for key, pbr in MATERIAIS_PBR.items():
            assert "cor"       in pbr
            assert "roughness" in pbr
            assert "metalness" in pbr
            assert 0.0 <= pbr["roughness"] <= 1.0
            assert 0.0 <= pbr["metalness"] <= 1.0

    def test_cromado_metalness_alto(self):
        assert MATERIAIS_PBR["cromado"]["metalness"] >= 0.9
        assert MATERIAIS_PBR["cromado"]["roughness"] <= 0.2

    def test_preto_metalness_baixo(self):
        assert MATERIAIS_PBR["preto"]["metalness"] <= 0.5


# ── Task 6.7: Endpoints (smoke tests sem server) ──────────────────────────────

class TestEndpoints:
    def test_export_3d_importa(self):
        """Router 3D deve ser importável sem erro."""
        from app.routers.viewer_3d import router
        assert router is not None

    def test_scene_builder_importa(self):
        from app.renderers.scene_builder import SceneBuilder
        assert SceneBuilder is not None

    def test_viewer_3d_no_main(self):
        """main.py deve incluir o router viewer_3d."""
        from pathlib import Path
        main = (Path(__file__).parent.parent / "app" / "main.py").read_text()
        assert "viewer_3d" in main

    def test_html_gerado(self):
        """_gerar_viewer_html deve retornar HTML válido com Three.js."""
        from app.routers.viewer_3d import _gerar_viewer_html
        scene = _scene("porta_pivotante_simples")
        html = _gerar_viewer_html(scene)
        assert "<!DOCTYPE html>" in html
        assert "three@0.165.0" in html or "three@0.128.0" in html  # r165 fotorrealista ou r128
        assert "OrbitControls" in html
        assert "SCENE_DATA" not in html  # data embutida como `const SCENE =`
        assert "const SCENE =" in html
        assert "toggleDoor" in html
        assert "screenshot" in html

    def test_html_tem_scene_data(self):
        """HTML deve conter os dados reais da cena."""
        from app.routers.viewer_3d import _gerar_viewer_html
        scene = _scene("porta_pivotante_simples")
        html = _gerar_viewer_html(scene)
        assert '"version":"1.0"' in html or '"version":"2.0"' in html
        assert "porta_pivotante_simples" in html

    def test_html_size_razoavel(self):
        """HTML não deve ser ridiculamente grande."""
        from app.routers.viewer_3d import _gerar_viewer_html
        scene = _scene("porta_pivotante_simples")
        html = _gerar_viewer_html(scene)
        size_kb = len(html) / 1024
        assert size_kb < 200, f"HTML muito grande: {size_kb:.1f}KB"
