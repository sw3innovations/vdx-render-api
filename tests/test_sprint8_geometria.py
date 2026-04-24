"""Sprint 8 — Geometry-by-Family tests for SceneBuilder."""
import pytest
from app.renderers.scene_builder import SceneBuilder, _detectar_familia
from app.models.render import RenderResponse, PecaRenderizada


def _resp(tipologia, pecas_data, classificacao="movel"):
    pecas = [
        PecaRenderizada(nome=n, largura_mm=w, altura_mm=h, classificacao=classificacao, ferragens=[])
        for n, w, h in pecas_data
    ]
    return RenderResponse(svg="", metadata={"tipologia_chave": tipologia, "layout_usado": "paralelas"}, pecas=pecas)


_sb = SceneBuilder()


class TestFamilyDetection:
    def test_porta_plana(self):
        assert _detectar_familia("porta_plana") == "porta"

    def test_porta_pivotante(self):
        assert _detectar_familia("porta_pivotante_simples") == "porta"

    def test_box_canto(self):
        assert _detectar_familia("box_canto_90") == "box_canto"

    def test_cobertura(self):
        assert _detectar_familia("cobertura_horizontal") == "cobertura"

    def test_sacada(self):
        assert _detectar_familia("fechamento_de_sacada_6_folhas") == "sacada"

    def test_guarda_corpo(self):
        assert _detectar_familia("guarda_corpo_linear") == "guarda_corpo"

    def test_balcao_duas(self):
        assert _detectar_familia("balcão_de_pia_duas_folhas") == "balcao"

    def test_balcao_quatro(self):
        assert _detectar_familia("balcão_de_pia_quatro_folhas") == "balcao"

    def test_divisoria(self):
        assert _detectar_familia("divisoria_porta_pivotante") == "divisoria"

    def test_vitrine(self):
        assert _detectar_familia("vitrine_movel") == "vitrine"

    def test_janela(self):
        assert _detectar_familia("janela_de_correr_2_folhas") == "janela"

    def test_especial_diametro(self):
        assert _detectar_familia("diâmetro") == "especial"


class TestVaoPresente:
    def test_porta_has_wall(self):
        s = _sb.build(_resp("porta_plana", [("Porta", 900, 2100)]))
        assert s["vao"]["presente"] is True

    def test_janela_has_wall(self):
        s = _sb.build(_resp("janela_de_correr_2_folhas", [("Folha 1", 600, 1200), ("Folha 2", 600, 1200)]))
        assert s["vao"]["presente"] is True

    def test_box_canto_no_wall(self):
        s = _sb.build(_resp("box_canto_90", [("Folha 1", 750, 2100), ("Folha 2", 750, 2100)]))
        assert s["vao"]["presente"] is False

    def test_cobertura_no_wall(self):
        s = _sb.build(_resp("cobertura_horizontal", [("Porta", 1500, 1000)]))
        assert s["vao"]["presente"] is False

    def test_sacada_no_wall(self):
        s = _sb.build(_resp("fechamento_de_sacada_6_folhas", [(f"Folha {i+1}", 500, 2100) for i in range(6)]))
        assert s["vao"]["presente"] is False

    def test_guarda_corpo_no_wall(self):
        s = _sb.build(_resp("guarda_corpo_linear", [("Porta", 1500, 1100)]))
        assert s["vao"]["presente"] is False

    def test_balcao_no_wall(self):
        s = _sb.build(_resp("balcão_de_pia_quatro_folhas", [(f"Folha {i+1}", 300, 700) for i in range(4)]))
        assert s["vao"]["presente"] is False

    def test_divisoria_no_wall(self):
        s = _sb.build(_resp("divisoria_porta_pivotante", [("Porta", 1500, 2100)]))
        assert s["vao"]["presente"] is False


class TestBoxCantoGeometry:
    def setup_method(self):
        self.scene = _sb.build(_resp("box_canto_90", [("Folha 1", 750, 2100), ("Folha 2", 750, 2100)]))

    def test_panel_count(self):
        assert len(self.scene["vidros"]) == 2

    def test_frontal_no_rotation(self):
        v1 = self.scene["vidros"][0]
        assert v1["rotacao"]["y"] == 0.0
        assert v1["rotacao"]["x"] == 0.0

    def test_lateral_rotated_90(self):
        v2 = self.scene["vidros"][1]
        assert v2["rotacao"]["y"] == 90.0

    def test_frontal_at_z_zero(self):
        v1 = self.scene["vidros"][0]
        assert v1["posicao"]["z"] == 0.0

    def test_lateral_x_at_corner(self):
        v2 = self.scene["vidros"][1]
        # x should be frontal_w/2 = 375
        assert v2["posicao"]["x"] == pytest.approx(375.0, abs=1)

    def test_lateral_z_negative(self):
        v2 = self.scene["vidros"][1]
        # z should be -lateral_w/2 = -375
        assert v2["posicao"]["z"] == pytest.approx(-375.0, abs=1)


class TestCoberturaGeometry:
    def setup_method(self):
        self.scene = _sb.build(_resp("cobertura_horizontal", [("Porta", 1500, 1000)]))

    def test_panel_count(self):
        assert len(self.scene["vidros"]) == 1

    def test_rotacao_x_minus90(self):
        v = self.scene["vidros"][0]
        assert v["rotacao"]["x"] == -90.0

    def test_installed_at_height(self):
        v = self.scene["vidros"][0]
        # Should be at approximately 2200mm height
        assert v["posicao"]["y"] == pytest.approx(2200.0, abs=50)

    def test_extends_back_in_z(self):
        v = self.scene["vidros"][0]
        # z center at -depth/2
        assert v["posicao"]["z"] < 0


class TestSacadaGeometry:
    def setup_method(self):
        self.scene = _sb.build(_resp(
            "fechamento_de_sacada_6_folhas",
            [(f"Folha {i+1}", 500, 2100) for i in range(6)]
        ))

    def test_panel_count(self):
        assert len(self.scene["vidros"]) == 6

    def test_panels_vertical(self):
        for v in self.scene["vidros"]:
            assert v["rotacao"]["x"] == 0.0
            assert v["rotacao"]["y"] == 0.0

    def test_no_wall(self):
        assert self.scene["vao"]["presente"] is False


class TestBalcaoGeometry:
    def test_duas_folhas_panel_count(self):
        s = _sb.build(_resp("balcão_de_pia_duas_folhas", [("Folha 1", 600, 700), ("Folha 2", 600, 700)]))
        assert len(s["vidros"]) == 2

    def test_quatro_folhas_panel_count(self):
        s = _sb.build(_resp("balcão_de_pia_quatro_folhas", [(f"Folha {i+1}", 300, 700) for i in range(4)]))
        assert len(s["vidros"]) == 4

    def test_panels_vertical(self):
        s = _sb.build(_resp("balcão_de_pia_duas_folhas", [("Folha 1", 600, 700), ("Folha 2", 600, 700)]))
        for v in s["vidros"]:
            assert v["rotacao"]["x"] == 0.0
            assert v["rotacao"]["y"] == 0.0


class TestPortaPlanaUnchanged:
    """Regression: porta_plana must behave as before."""

    def test_single_panel(self):
        s = _sb.build(_resp("porta_plana", [("Porta", 900, 2100)]))
        assert len(s["vidros"]) == 1

    def test_panel_centered_x(self):
        s = _sb.build(_resp("porta_plana", [("Porta", 900, 2100)]))
        assert s["vidros"][0]["posicao"]["x"] == pytest.approx(0.0, abs=1)

    def test_panel_no_rotation(self):
        s = _sb.build(_resp("porta_plana", [("Porta", 900, 2100)]))
        rot = s["vidros"][0]["rotacao"]
        assert rot == {"x": 0.0, "y": 0.0, "z": 0.0}

    def test_has_wall(self):
        s = _sb.build(_resp("porta_plana", [("Porta", 900, 2100)]))
        assert s["vao"]["presente"] is True

    def test_scene_version(self):
        s = _sb.build(_resp("porta_plana", [("Porta", 900, 2100)]))
        assert s["version"] == "2.0"
