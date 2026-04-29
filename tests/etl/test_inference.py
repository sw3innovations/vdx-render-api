"""Tests for inference transformers — Sprint 10."""
from app.etl.transformers.inference import inferir_nome_modelo, inferir_nome_valido, inferir_tipo_peca


def test_inferir_nome_modelo_valido():
    nome = inferir_nome_modelo(100, "JANELA DE CORRER", 2, 1)
    assert "JANELA DE CORRER" in nome
    assert "2F" in nome


def test_inferir_nome_modelo_ds_mod_interrogacao():
    nome = inferir_nome_modelo(100, "?", 2, 1)
    assert "100" in nome


def test_inferir_nome_valido_normal():
    assert inferir_nome_valido("JANELA DE CORRER") is True


def test_inferir_nome_valido_interrogacao():
    assert inferir_nome_valido("?") is False


def test_inferir_nome_valido_none():
    assert inferir_nome_valido(None) is False


def test_inferir_nome_valido_vazio():
    assert inferir_nome_valido("") is False


def test_inferir_tipo_peca_de_ds_tipo():
    assert inferir_tipo_peca("VI", "VID") == "VI"


def test_inferir_tipo_peca_fallback_ds_peca():
    assert inferir_tipo_peca(None, "VID") == "VID"


def test_inferir_tipo_peca_nenhum():
    assert inferir_tipo_peca(None, None) is None
