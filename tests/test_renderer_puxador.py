"""
Testes de desenho dinâmico de puxadores (Sprint 8 Entrega 3).

Formas esperadas:
  - CÍRCULO  : diametro > 0 e (comprimento == 0 ou comprimento <= diametro)
  - CÁPSULA  : diametro > 0 e 0 < comprimento < 100
  - BARRA    : comprimento >= 100
  - FALLBACK : dimensões vazias ou None
"""
import os
import pytest

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

ACAB = "#90B0C8"
SC = 0.18


# ─── desenhar_puxador_dinamico ────────────────────────────────────────────────

def test_desenhar_puxador_circulo_quando_diametro_sem_comprimento():
    from app.renderers._helpers_ferragens import desenhar_puxador_dinamico
    svg = desenhar_puxador_dinamico({"diametro": 18, "comprimento": None}, 100, 200, SC, ACAB)
    assert "<circle" in svg
    assert "<!-- puxador padrão" not in svg


def test_desenhar_puxador_barra_quando_comprimento_grande():
    from app.renderers._helpers_ferragens import desenhar_puxador_dinamico
    svg = desenhar_puxador_dinamico({"diametro": None, "comprimento": 300}, 100, 200, SC, ACAB)
    assert "<rect" in svg
    assert "<!-- puxador padrão" not in svg


def test_desenhar_puxador_capsula_quando_compacto():
    from app.renderers._helpers_ferragens import desenhar_puxador_dinamico
    svg = desenhar_puxador_dinamico({"diametro": 18, "comprimento": 50}, 100, 200, SC, ACAB)
    assert "<rect" in svg
    assert "<!-- puxador padrão" not in svg


def test_desenhar_puxador_fallback_quando_dimensoes_vazias():
    from app.renderers._helpers_ferragens import desenhar_puxador_dinamico
    svg = desenhar_puxador_dinamico({}, 100, 200, SC, ACAB)
    assert "<!-- puxador padrão (sem dimensões) -->" in svg
    assert "<line" in svg


def test_desenhar_puxador_fallback_quando_tudo_none():
    from app.renderers._helpers_ferragens import desenhar_puxador_dinamico
    svg = desenhar_puxador_dinamico(
        {"diametro": None, "comprimento": None, "largura": None},
        100, 200, SC, ACAB
    )
    assert "<!-- puxador padrão (sem dimensões) -->" in svg


# ─── buscar_dimensoes_puxador ─────────────────────────────────────────────────

def test_buscar_dimensoes_puxador_existente_retorna_dict():
    from app.services.ferragem_lookup import buscar_dimensoes_puxador
    result = buscar_dimensoes_puxador("PUXADOR 400")
    assert result is not None
    assert isinstance(result, dict)
    assert result.get("comprimento") == 400


def test_buscar_dimensoes_puxador_inexistente_retorna_none():
    from app.services.ferragem_lookup import buscar_dimensoes_puxador
    result = buscar_dimensoes_puxador("CODIGO_INEXISTENTE_99999")
    assert result is None


def test_buscar_dimensoes_com_fabricante_especifico():
    from app.services.ferragem_lookup import buscar_dimensoes_puxador
    result = buscar_dimensoes_puxador("PUXADOR 300", "HE")
    assert result is not None
    assert result.get("comprimento") == 300


# ─── Integração com render() ──────────────────────────────────────────────────

def test_render_porta_abrir_com_puxador_codigo_substitui_desenho():
    from app.renderers.svg_renderer_v2 import render
    svg_sem = render("porta_abrir", 900, 2100)
    svg_com = render("porta_abrir", 900, 2100, puxador_codigo="PUXADOR 400")
    assert svg_sem != svg_com


def test_render_porta_abrir_sem_puxador_codigo_mantem_padrao():
    from app.renderers.svg_renderer_v2 import render
    svg = render("porta_abrir", 900, 2100)
    assert "<svg" in svg


def test_render_com_codigo_inexistente_fallback_padrao_sem_quebrar():
    from app.renderers.svg_renderer_v2 import render
    svg = render("porta_abrir", 900, 2100, puxador_codigo="CODIGO_INEXISTENTE_99999")
    assert "<svg" in svg
    assert "<!-- puxador padrão (sem dimensões) -->" in svg
