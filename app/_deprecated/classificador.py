"""
Classificador de peças de vidro — determina se é FIXA ou MÓVEL.
Regra: na dúvida, é fixa (segurança — não fazer furo desnecessário).
"""

NOMES_FIXAS = {
    "fixo", "bandeira", "painel", "lateral fixa", "vidro fixo",
    "lateral", "fixo 1", "fixo 2", "folha fixa"
}

NOMES_MOVEIS = {
    "porta", "movel", "folha movel", "pivotante", "basculante",
    "maxim-ar", "maxim ar", "folha 2", "móvel"
}

NOMES_CORRER = {
    "folha de correr", "correr", "deslizante"
}


def classificar_peca(nome_peca: str, tipologia_nome: str = "") -> str:
    """
    Retorna 'fixa', 'movel' ou 'correr'.
    Regra: na dúvida, é fixa (segurança — não fazer furo desnecessário).
    """
    nome = nome_peca.strip().lower()
    tip = tipologia_nome.strip().lower()

    if any(f in nome for f in NOMES_FIXAS):
        return "fixa"
    if any(m in nome for m in NOMES_MOVEIS):
        return "movel"
    if any(c in nome for c in NOMES_CORRER):
        return "correr"

    # Inferência por tipologia
    if "box" in tip and "porta" in nome:
        return "movel"

    if "correr" in tip:
        if "1" in nome or "fixa" in nome:
            return "fixa"
        if "2" in nome or "movel" in nome:
            return "correr"

    if "guarda" in tip:
        return "fixa"

    if "cobertura" in tip or "claraboia" in tip:
        return "fixa"

    # Default: fixa (segurança)
    return "fixa"
