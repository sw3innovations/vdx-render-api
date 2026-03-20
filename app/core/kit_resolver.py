"""
Resolver de kits de ferragens por tipologia.
"""
from typing import Optional
from app.core.skill_vidracaria import normalizar_para_skill

KITS = {
    "porta_pivotante_simples": {
        "codigo": "KIT_01",
        "nome": "Kit Porta Pivotante Simples V/A",
        "itens": [
            {"codigo": "1201", "nome": "Pivô superior", "qtd": 1},
            {"codigo": "1101", "nome": "Dobradiça superior", "qtd": 1},
            {"codigo": "1103", "nome": "Dobradiça inferior", "qtd": 1},
            {"codigo": "1013", "nome": "Pivô inferior", "qtd": 1},
            {"codigo": "1520", "nome": "Fechadura central", "qtd": 1},
        ],
        "puxador_separado": True,
    },
    "porta_dupla_pivotante": {
        "codigo": "KIT_02",
        "nome": "Kit Porta Pivotante Dupla c/ Bandeira",
        "itens": [
            {"codigo": "1201", "nome": "Pivô superior", "qtd": 2},
            {"codigo": "1101", "nome": "Dobradiça superior", "qtd": 2},
            {"codigo": "1103", "nome": "Dobradiça inferior", "qtd": 2},
            {"codigo": "1013", "nome": "Pivô inferior", "qtd": 2},
            {"codigo": "1520", "nome": "Fechadura central", "qtd": 1},
        ],
        "puxador_separado": True,
    },
    "box_frontal_2_folhas": {
        "codigo": "KIT_05",
        "nome": "Kit Box Frontal 2 Folhas",
        "itens": [
            {"codigo": "1114", "nome": "Dobradiça automática", "qtd": 2},
            {"codigo": "1629B", "nome": "Bate-fecha", "qtd": 1},
        ],
        "puxador_separado": True,
    },
    "box_canto_l": {
        "codigo": "KIT_03",
        "nome": "Kit Box Canto 90°",
        "itens": [
            {"codigo": "1114", "nome": "Dobradiça automática", "qtd": 2},
            {"codigo": "1302", "nome": "Suporte de canto", "qtd": 2},
            {"codigo": "1629B", "nome": "Bate-fecha", "qtd": 1},
        ],
        "puxador_separado": True,
    },
    "porta_correr_simples": {
        "codigo": "KIT_09",
        "nome": "Kit Porta de Correr 2 Folhas",
        "itens": [
            {"codigo": "3530", "nome": "Roldana simples", "qtd": 2},
            {"codigo": "1629B", "nome": "Bate-fecha", "qtd": 1},
            {"codigo": "3534", "nome": "Trinco", "qtd": 1},
        ],
        "puxador_separado": True,
    },
    "janela_correr_2_folhas": {
        "codigo": "KIT_05V",
        "nome": "Kit Janela Correr 2 Folhas",
        "itens": [
            {"codigo": "1125", "nome": "Roldana simples", "qtd": 2},
            {"codigo": "1629B", "nome": "Bate-fecha janela", "qtd": 1},
            {"codigo": "1038", "nome": "Capuchinho", "qtd": 2},
        ],
        "puxador_separado": False,
    },
    "janela_basculante": {
        "codigo": "KIT_06",
        "nome": "Kit Janela Basculante",
        "itens": [
            {"codigo": "1335T", "nome": "Trinco basculante", "qtd": 1},
            {"codigo": "1500", "nome": "Suporte de abertura", "qtd": 1},
        ],
        "puxador_separado": False,
    },
    "janela_maxim_ar": {
        "codigo": "KIT_07",
        "nome": "Kit Janela Maxim-Ar",
        "itens": [
            {"codigo": "1335T", "nome": "Trinco", "qtd": 1},
            {"codigo": "1500", "nome": "Braço articulado", "qtd": 2},
        ],
        "puxador_separado": False,
    },
    "janela_pivotante": {
        "codigo": "KIT_01J",
        "nome": "Kit Janela Pivotante",
        "itens": [
            {"codigo": "1101", "nome": "Dobradiça superior", "qtd": 1},
            {"codigo": "1103", "nome": "Dobradiça inferior", "qtd": 1},
            {"codigo": "1520", "nome": "Fechadura", "qtd": 1},
        ],
        "puxador_separado": True,
    },
    "guarda_corpo_reto": {
        "codigo": "NENHUM",
        "nome": "Sem kit — fixação por coluna/base",
        "itens": [],
        "puxador_separado": False,
    },
    "guarda_corpo_linear": {
        "codigo": "NENHUM",
        "nome": "Sem kit — fixação por coluna/base",
        "itens": [],
        "puxador_separado": False,
    },
    "paineis_lineares": {
        "codigo": "NENHUM",
        "nome": "Sem kit — painéis fixos",
        "itens": [],
        "puxador_separado": False,
    },
    "divisoria_porta_pivotante": {
        "codigo": "KIT_01",
        "nome": "Kit Porta Pivotante (divisória)",
        "itens": [
            {"codigo": "1201", "nome": "Pivô superior", "qtd": 1},
            {"codigo": "1101", "nome": "Dobradiça superior", "qtd": 1},
            {"codigo": "1103", "nome": "Dobradiça inferior", "qtd": 1},
            {"codigo": "1013", "nome": "Pivô inferior", "qtd": 1},
            {"codigo": "1520", "nome": "Fechadura central", "qtd": 1},
        ],
        "puxador_separado": True,
    },
}


def resolver_kit(tipologia_nome: str):
    """Retorna dict do kit ou None se não encontrado."""
    if not tipologia_nome:
        return None

    import unicodedata
    nome_norm = unicodedata.normalize('NFD', tipologia_nome.lower())
    nome_norm = ''.join(c for c in nome_norm if unicodedata.category(c) != 'Mn')
    nome_norm = nome_norm.replace(' ', '_').replace('-', '_')

    # Verificação direta das chaves de janela (antes de delegar ao normalizar_para_skill
    # que pode mapear "janela correr" para "porta_correr_*")
    if "janela_correr" in nome_norm or ("janela" in nome_norm and "correr" in nome_norm):
        if "4_folhas" in nome_norm or "4folhas" in nome_norm:
            return KITS.get("janela_correr_2_folhas")  # mesmo kit
        return KITS.get("janela_correr_2_folhas")
    if "janela_basculante" in nome_norm or ("janela" in nome_norm and "basculante" in nome_norm):
        return KITS.get("janela_basculante")
    if "janela_maxim" in nome_norm or ("janela" in nome_norm and "maxim" in nome_norm):
        return KITS.get("janela_maxim_ar")
    if "janela_pivotante" in nome_norm or ("janela" in nome_norm and "pivotante" in nome_norm):
        return KITS.get("janela_pivotante")

    chave = normalizar_para_skill(tipologia_nome)
    return KITS.get(chave)
