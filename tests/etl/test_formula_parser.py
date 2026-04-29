"""Tests for formula_parser — Sprint 10."""
from app.etl.transformers.formula_parser import normalizar_formula, extrair_variaveis


def test_normalizar_altura_simples():
    assert normalizar_formula("ALTURA-10") == "ALTURA_VAO-10"


def test_normalizar_largura_simples():
    assert normalizar_formula("LARGURA/2") == "LARGURA_VAO/2"


def test_normalizar_altura_do_vao():
    assert normalizar_formula("ALTURA DO VÃO * 0.5") == "ALTURA_VAO * 0.5"


def test_normalizar_sacada():
    f = normalizar_formula("SACADA + 50")
    assert "ALTURA_SACADA" in f


def test_normalizar_none_retorna_none():
    assert normalizar_formula(None) is None


def test_normalizar_vazio_retorna_vazio():
    assert normalizar_formula("") == ""


def test_extrair_variaveis_altura():
    vars_ = extrair_variaveis("ALTURA_VAO - 10")
    assert "ALTURA_VAO" in vars_


def test_extrair_variaveis_multiplas():
    vars_ = extrair_variaveis("ALTURA_VAO * 2 + LARGURA_VAO")
    assert "ALTURA_VAO" in vars_
    assert "LARGURA_VAO" in vars_


def test_extrair_variaveis_formula_nula():
    assert extrair_variaveis(None) == []


def test_token_mais_longo_tem_prioridade():
    # "ALTURA SACADA" deve mapear para ALTURA_SACADA, não ALTURA_VAO
    result = normalizar_formula("ALTURA SACADA / 2")
    assert "ALTURA_SACADA" in result
    assert "ALTURA_VAO" not in result
