"""Tests for deduplicator — Sprint 10."""
from app.etl.transformers.deduplicator import (
    normalizar_codigo_ferragem,
    similaridade_bigram,
    sao_duplicatas,
    agrupar_por_codigo,
)


def test_normalizar_remove_hifens():
    assert normalizar_codigo_ferragem("QT-001") == "QT001"


def test_normalizar_remove_espacos():
    assert normalizar_codigo_ferragem("QT 001") == "QT001"


def test_normalizar_maiusculo():
    assert normalizar_codigo_ferragem("qt001") == "QT001"


def test_normalizar_none_retorna_none():
    assert normalizar_codigo_ferragem(None) is None


def test_similaridade_identico():
    assert similaridade_bigram("PUXADOR BARRA", "PUXADOR BARRA") == 1.0


def test_similaridade_diferente():
    s = similaridade_bigram("PUXADOR BARRA", "DOBRADIÇA PIANO")
    assert s < 0.5


def test_similaridade_parecido():
    s = similaridade_bigram("PUXADOR BARRA 300", "PUXADOR BARRA 301")
    assert s > 0.8


def test_sao_duplicatas_por_codigo():
    assert sao_duplicatas("A", "B", codigo_a="QT-001", codigo_b="QT001") is True


def test_nao_sao_duplicatas_distintos():
    assert sao_duplicatas("PUXADOR BARRA", "DOBRADIÇA 100", codigo_a="A1", codigo_b="B2") is False


def test_agrupar_por_codigo_agrupa():
    recs = [
        {"codigo": "QT-001", "nome": "Puxador A"},
        {"codigo": "QT001",  "nome": "Puxador A variant"},
        {"codigo": "ZZ-999", "nome": "Outro"},
    ]
    grupos = agrupar_por_codigo(recs)
    assert "QT001" in grupos
    assert len(grupos["QT001"]) == 2


def test_agrupar_sem_codigo():
    recs = [{"nome": "Sem código"}]
    grupos = agrupar_por_codigo(recs)
    assert "SEM_CODIGO" in grupos
