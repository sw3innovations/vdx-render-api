"""Testes para tipologia_cleaner — Sprint 11 Fase 1.5."""
import os
import pytest

os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

from app.etl.transformers.tipologia_cleaner import normalizar_nome, avaliar_tipologia_dump


# ── normalizar_nome ───────────────────────────────────────────────────────────

def test_normalizar_nome_remove_dimensoes_entre_parenteses():
    assert normalizar_nome("JANELA 4 FOLHAS (-20 -60)") == "Janela 4 Folhas"


def test_normalizar_nome_capitaliza_corretamente():
    assert normalizar_nome("PORTAS DE CORRER") == "Portas de Correr"


def test_normalizar_nome_aplica_acentos_dominio():
    assert "Diâmetro" in normalizar_nome("DIAMETRO/OVAL")


def test_normalizar_nome_preserva_palavras_minusculas_pt_br():
    result = normalizar_nome("PORTA DE ABRIR COM BANDEIRA")
    assert result == "Porta de Abrir com Bandeira"


# ── avaliar_tipologia_dump ────────────────────────────────────────────────────

def test_avaliar_rejeita_moldes_valores_a_confirmar():
    r = avaliar_tipologia_dump("MOLDES (VALORES A CONFIRMAR)", "TIP_0016_X")
    assert r["acao"] == "REJEITAR"
    assert "motivo" in r


def test_avaliar_rejeita_metacategorias_portas_janelas_box():
    for nome_meta in ("PORTAS", "JANELAS", "BOX", "FIXOS"):
        r = avaliar_tipologia_dump(nome_meta, f"TIP_META_{nome_meta}")
        assert r["acao"] == "REJEITAR", f"{nome_meta} deveria ser rejeitada"


def test_avaliar_mescla_pivotante_dump_com_porta_pivotante_simples():
    r = avaliar_tipologia_dump("PIVOTANTE", "TIP_0005_PIVOTANTE")
    assert r["acao"] == "MESCLAR"
    assert r["destino_codigo"] == "porta_pivotante_simples"


def test_avaliar_aceita_sanfonado_com_nome_normalizado():
    r = avaliar_tipologia_dump("SANFONADO", "TIP_0015_SANFONADO")
    assert r["acao"] == "ACEITAR"
    assert r["nome_normalizado"] == "Sanfonado"


# ── integração com CanonicalLoader ───────────────────────────────────────────

@pytest.fixture(scope="module")
def loader_stats_clean():
    """Roda o ETL com cleaner ativo e retorna stats + conn."""
    from app.etl.loaders.load_canonical import CanonicalLoader
    with CanonicalLoader() as loader:
        loader.reset()
        stats = loader.run()
    return stats


def test_loader_apos_limpeza_nao_tem_lixo(loader_stats_clean):
    from app.core.constitution import _get_conn
    conn = _get_conn()
    nomes_lixo = ("PORTAS", "JANELAS", "BOX", "FIXOS", "MOLDES (VALORES A CONFIRMAR)")
    for nome in nomes_lixo:
        row = conn.execute(
            "SELECT codigo FROM tipologias_canonicas WHERE nome_apresentacao = ?", (nome,)
        ).fetchone()
        assert row is None, f"Lixo '{nome}' ainda presente na canonical"
    conn.close()


def test_loader_pivotante_dump_mescla_em_porta_pivotante_simples_constitution(loader_stats_clean):
    from app.core.constitution import _get_conn
    conn = _get_conn()
    row = conn.execute(
        "SELECT fonte_origem, nu_tip_dump FROM tipologias_canonicas WHERE codigo = 'porta_pivotante_simples'"
    ).fetchone()
    assert row is not None, "porta_pivotante_simples não encontrada"
    assert row[0] == "ambos", f"fonte_origem deveria ser 'ambos', foi '{row[0]}'"
    assert row[1] is not None, "nu_tip_dump deveria estar preenchido após mesclagem"
    conn.close()
