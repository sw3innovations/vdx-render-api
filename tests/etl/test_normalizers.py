"""Unit tests for ETL normalizers — Sprint 10."""
import os
os.environ.setdefault("VDX_API_MASTER_KEY", "")
os.environ.setdefault("VDX_VIEW_TOKEN_SECRET", "test-secret-32chars-xxxxxxxxxx")

from app.etl.normalizers.canonical_materials import normalizar_material, SEED_MATERIAIS
from app.etl.normalizers.canonical_acabamentos import normalizar_acabamento, SEED_ACABAMENTOS
from app.etl.normalizers.canonical_variaveis import normalizar_variavel, SEED_VARIAVEIS
from app.etl.normalizers.canonical_tipologias import ds_tmd_to_codigo, inferir_categoria


# ── materiais ─────────────────────────────────────────────────────────────────

def test_material_aco_inox():
    assert normalizar_material("aco inox") == "ACO_INOX"

def test_material_aluminio_acentuado():
    assert normalizar_material("Alumínio") == "ALUMINIO"

def test_material_inox_variante():
    assert normalizar_material("inox") == "ACO_INOX"

def test_material_zamak():
    assert normalizar_material("zamak") == "ZAMAK"

def test_material_desconhecido_retorna_outro():
    assert normalizar_material("fibra de carbono") == "OUTRO"

def test_material_none_retorna_outro():
    assert normalizar_material(None) == "OUTRO"

def test_material_vazio_retorna_outro():
    assert normalizar_material("") == "OUTRO"

def test_seed_materiais_sem_duplicatas():
    codigos = [m[0] for m in SEED_MATERIAIS]
    assert len(codigos) == len(set(codigos))


# ── acabamentos ───────────────────────────────────────────────────────────────

def test_acabamento_polido():
    assert normalizar_acabamento("polido") == "POLIDO"

def test_acabamento_escovado():
    assert normalizar_acabamento("Escovado") == "ESCOVADO"

def test_acabamento_preto():
    assert normalizar_acabamento("preto") == "PRETO"

def test_acabamento_cromado():
    assert normalizar_acabamento("chrome") == "CROMADO"

def test_acabamento_desconhecido_retorna_outro():
    assert normalizar_acabamento("marrom oxidado") == "OUTRO"

def test_acabamento_none_retorna_outro():
    assert normalizar_acabamento(None) == "OUTRO"

def test_seed_acabamentos_sem_duplicatas():
    codigos = [a[0] for a in SEED_ACABAMENTOS]
    assert len(codigos) == len(set(codigos))


# ── variaveis ─────────────────────────────────────────────────────────────────

def test_variavel_altura():
    assert normalizar_variavel("altura") == "ALTURA_VAO"

def test_variavel_largura_acentuada():
    assert normalizar_variavel("largura do vão") == "LARGURA_VAO"

def test_variavel_sacada():
    assert normalizar_variavel("sacada") == "ALTURA_SACADA"

def test_variavel_desconhecida_uppercased():
    result = normalizar_variavel("minha_var_custom")
    assert result == result.upper()

def test_variavel_none_retorna_desconhecida():
    assert normalizar_variavel(None) == "DESCONHECIDA"

def test_seed_variaveis_eixos_validos():
    eixos_validos = {"altura", "largura", "neutro"}
    for _, _, eixo in SEED_VARIAVEIS:
        assert eixo in eixos_validos


# ── tipologias ────────────────────────────────────────────────────────────────

def test_ds_tmd_to_codigo_basico():
    codigo = ds_tmd_to_codigo(100, "JANELA DE CORRER 2 FOLHAS")
    assert codigo.startswith("TIP_0100_")
    assert codigo == codigo.upper()

def test_ds_tmd_to_codigo_sem_nome():
    assert ds_tmd_to_codigo(5, None) == "TIP_0005"

def test_inferir_categoria_janela():
    assert inferir_categoria("JANELA DE CORRER 2 FOLHAS") == "JANELA"

def test_inferir_categoria_porta():
    assert inferir_categoria("PORTA DE ABRIR SIMPLES") == "PORTA"

def test_inferir_categoria_none():
    assert inferir_categoria(None) is None

def test_inferir_categoria_desconhecida():
    assert inferir_categoria("ESTRUTURA ESPECIAL XYZ") is None
