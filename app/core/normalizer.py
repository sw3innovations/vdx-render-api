"""
Normalizador Inteligente — classifica peças e tipologias em 3 camadas.
Funciona com qualquer variação de nome e auto-cresce via aliases.
"""
import unicodedata
import logging
from typing import Optional
from app.core import constitution

log = logging.getLogger(__name__)

# Keywords de classificação de peças — tokens que determinam a classe
KEYWORDS_CLASSIFICACAO = {
    "fixa": ["fixo", "fixa", "bandeira", "painel", "lateral", "vidro fixo",
             "folha fixa", "fixo 1", "fixo 2", "estatico", "estacionario"],
    "movel": ["porta", "movel", "movel", "pivotante", "abrir", "giro",
              "folha movel"],
    "correr": ["correr", "deslizante", "folha de correr", "sliding"],
    "basculante": ["basculante", "maxim", "projetante"],
}

# Keywords de tipologia — tokens que identificam a família
KEYWORDS_TIPOLOGIA = {
    "porta_pivotante_simples": ["porta", "pivotante"],
    "porta_pivotante_dupla_bandeira": ["porta", "pivotante", "dupla", "bandeira"],
    "box_frontal_2_folhas": ["box", "frontal"],
    "box_canto_90": ["box", "canto"],
    "porta_correr_2_folhas": ["porta", "correr"],
    "janela_correr_2_folhas": ["janela", "correr"],
    "janela_basculante": ["janela", "basculante"],
    "janela_maxim_ar": ["janela", "maxim"],
    "janela_pivotante": ["janela", "pivotante"],
    "guarda_corpo_linear": ["guarda", "corpo"],
    "cobertura": ["cobertura", "claraboia", "marquise", "telhado"],
    "divisoria_porta_pivotante": ["divisoria"],
}

# Ordem de especificidade (mais específico primeiro para evitar match errado)
_TIPOLOGIA_PRIORITY = [
    "porta_pivotante_dupla_bandeira",
    "box_canto_90",
    "porta_correr_2_folhas",
    "janela_correr_2_folhas",
    "janela_basculante",
    "janela_maxim_ar",
    "janela_pivotante",
    "guarda_corpo_linear",
    "cobertura",
    "divisoria_porta_pivotante",
    "box_frontal_2_folhas",
    "porta_pivotante_simples",
]


def _tokenizar(nome: str) -> list[str]:
    """Normaliza e tokeniza: 'PORTA DIREITA' → ['porta', 'direita']"""
    nome = unicodedata.normalize('NFD', nome.lower().strip())
    nome = ''.join(c for c in nome if unicodedata.category(c) != 'Mn')
    nome = nome.replace('-', ' ').replace('_', ' ').replace('/', ' ')
    return [t for t in nome.split() if len(t) > 1]


def classificar_peca(nome_peca: str, tipologia_dados: dict = None) -> str:
    """
    Classifica peça em 3 camadas:
    1. Match direto na Constitution (classificacao_pecas da tipologia)
    2. Match por tokens (keywords)
    3. Default seguro (fixa)
    """
    nome = nome_peca.strip().lower()
    tokens = _tokenizar(nome_peca)

    # CAMADA 1: Match no mapa da tipologia
    if tipologia_dados:
        class_map = tipologia_dados.get("classificacao_pecas", {})
        # Match exato
        if nome in class_map:
            return class_map[nome]
        # Match substring (key contida no nome ou vice-versa)
        for key, cls in class_map.items():
            if key in nome or nome in key:
                return cls
        # Match por token (qualquer token da peça casa com key do mapa)
        for key, cls in class_map.items():
            key_tokens = _tokenizar(key)
            if any(kt in tokens for kt in key_tokens):
                alias = nome.replace(' ', '_')
                constitution.registrar_alias(alias, cls, "classificacao_peca", origem="token_match")
                log.info(f"Auto-alias peca: '{nome}' → '{cls}' (token match em '{key}')")
                return cls

    # CAMADA 2: Keywords globais
    for cls, keywords in KEYWORDS_CLASSIFICACAO.items():
        if any(kw in tokens or kw in nome for kw in keywords):
            alias = nome.replace(' ', '_')
            constitution.registrar_alias(alias, cls, "classificacao_peca", origem="keyword_match")
            log.info(f"Auto-alias peca: '{nome}' → '{cls}' (keyword match)")
            if cls == "basculante":
                return "movel"  # basculante é subtipo de móvel
            return cls

    # CAMADA 3: Alias na Constitution
    alias_key = nome.replace(' ', '_')
    alias_cls = constitution.normalizar(alias_key, tipo="classificacao_peca")
    if alias_cls in ("fixa", "movel", "correr"):
        return alias_cls

    # Default: fixa (segurança — não faz furo desnecessário)
    log.warning(f"Peca '{nome_peca}' nao classificada — default fixa")
    return "fixa"


def normalizar_tipologia(tipologia_nome: str) -> tuple[str, Optional[dict]]:
    """
    Normaliza tipologia em 3 camadas:
    1. Match direto na Constitution (aliases)
    2. Match por tokens (keywords) — maior score ganha
    3. None (caller decide: Claude ou fallback)

    Retorna (chave_canonica, dados_constitution_ou_None)
    """
    if not tipologia_nome:
        return "", None

    # CAMADA 1: Constitution aliases
    chave = constitution.normalizar(tipologia_nome, tipo="tipologia")
    entry = constitution.buscar(chave, tipo="tipologia")
    if entry and entry.get("confianca", 0) >= 0.5:
        return chave, entry["dados"]

    # CAMADA 2: Token matching (por ordem de especificidade)
    tokens = _tokenizar(tipologia_nome)
    melhor_match = None
    melhor_score = 0

    for canonical in _TIPOLOGIA_PRIORITY:
        keywords = KEYWORDS_TIPOLOGIA.get(canonical, [])
        score = sum(1 for kw in keywords if kw in tokens)
        if score > melhor_score:
            melhor_score = score
            melhor_match = canonical

    if melhor_match and melhor_score >= 2:
        entry = constitution.buscar(melhor_match, tipo="tipologia")
        if entry:
            alias_key = tipologia_nome.lower().strip().replace(' ', '_').replace('-', '_')
            constitution.registrar_alias(alias_key, melhor_match, "tipologia", origem="token_match")
            log.info(f"Auto-alias tipologia: '{tipologia_nome}' → '{melhor_match}' (score={melhor_score})")
            return melhor_match, entry["dados"]

    # Score 1 — tenta match single-token pra tipologias com keyword única
    if melhor_match and melhor_score == 1:
        # Só aceita com score 1 se a keyword for muito específica
        keywords = KEYWORDS_TIPOLOGIA.get(melhor_match, [])
        specific_singles = ["cobertura", "claraboia", "marquise", "telhado",
                            "basculante", "maxim", "divisoria", "guarda"]
        if any(kw in tokens for kw in specific_singles):
            entry = constitution.buscar(melhor_match, tipo="tipologia")
            if entry:
                alias_key = tipologia_nome.lower().strip().replace(' ', '_').replace('-', '_')
                constitution.registrar_alias(alias_key, melhor_match, "tipologia", origem="token_match")
                log.info(f"Auto-alias tipologia (single): '{tipologia_nome}' → '{melhor_match}'")
                return melhor_match, entry["dados"]

    # CAMADA 3: não encontrou
    return chave, None
