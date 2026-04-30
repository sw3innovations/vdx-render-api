"""Limpeza e normalização de tipologias vindas do dump ERP."""
from __future__ import annotations

import re

# DS_TMD values that are garbage (placeholders, meta-categories)
_LIXO_DUMP: frozenset[str] = frozenset({
    "MOLDES (VALORES A CONFIRMAR)",
    "VERSATICK TRUCK TRES FOLHAS",
    "REPOSICOE MEDIDAS FINAIS",
    "REPOSIÇÕE MEDIDAS FINAIS",
    "PORTAS",
    "JANELAS",
    "BOX",
    "FIXOS",
    "VIDROS",
    "MEDIDA FINAL",
    "PORTAS DE CORRER",
    "ESPELHOS",
    "ESPELHOS BISOTÊ",
    "ESPELHOS BISOTE",
})

# DS_TMD (uppercase) → codigo in constitution_entries that this dump entry duplicates
_DUP_DUMP_TO_CONSTITUTION: dict[str, str | None] = {
    "PIVOTANTE": "porta_pivotante_simples",
    "BASCULANTE": "janela_basculante",
    "MAXIM-AR": "janela_maxim_ar",
    "PORTA DE ABRIR": "porta_abrir",
    "PORTAS DE CORRER (E)": "porta_correr_2_folhas",
    "JANELA 2 FOLHAS": "janela_correr_2_folhas",
    "JANELA DE CORRER 2 FOLHAS": "janela_correr_2_folhas",
    "BOX PADRÃO": "box_de_giro",
    "BOX PADRAO": "box_de_giro",
    "BOX ENGENHARIA": "box_articulado",
}

_PALAVRAS_MINUSCULAS_PT_BR = frozenset({
    "de", "da", "do", "das", "dos", "e", "ou",
    "a", "o", "as", "os", "em", "com", "para",
})

_CORRECOES_ACENTO: dict[str, str] = {
    "Diametro": "Diâmetro",
    "Vao": "Vão",
    "Opcao": "Opção",
    "Sacada": "Sacada",
}


def normalizar_nome(nome_bruto: str) -> str:
    """Converte 'JANELA 4 FOLHAS (-20 -60)' → 'Janela 4 Folhas'.

    Passos: remove prefixo TIP_NNNN_, substitui underscores, remove conteúdo
    entre parênteses, aplica title case pt-BR, corrige acentos do domínio.
    """
    if not nome_bruto:
        return nome_bruto

    n = nome_bruto.strip()

    # Remove ETL-generated TIP_NNNN_ prefix
    n = re.sub(r"^TIP_\d+_", "", n)

    # Replace underscores with spaces (ETL codes use underscores as separators)
    n = n.replace("_", " ")

    # Remove parenthesized content (dimensions, variants)
    n = re.sub(r"\s*\([^)]*\)\s*", " ", n).strip()

    # Title case with pt-BR lowercase connectors
    words = n.lower().split()
    result = []
    for i, w in enumerate(words):
        if i == 0 or w not in _PALAVRAS_MINUSCULAS_PT_BR:
            result.append(w.capitalize())
        else:
            result.append(w)
    n = " ".join(result)

    # Domain accent corrections
    for wrong, correct in _CORRECOES_ACENTO.items():
        n = n.replace(wrong, correct)

    return n


def avaliar_tipologia_dump(ds_tmd: str | None, codigo: str) -> dict:
    """Decide o que fazer com uma tipologia do dump.

    Retorna dict com chave 'acao':
      - 'REJEITAR': lixo/metacategoria, não inserir
      - 'MESCLAR': duplicata de tipologia do constitution
      - 'ACEITAR': inserir com nome normalizado

    Matching order: exact → strip-clean (parens stripped) → ACEITAR.
    """
    ds_upper = (ds_tmd or "").upper().strip()

    if ds_upper in _LIXO_DUMP:
        return {"acao": "REJEITAR", "motivo": "lixo_ou_metacategoria"}

    if ds_upper in _DUP_DUMP_TO_CONSTITUTION:
        destino = _DUP_DUMP_TO_CONSTITUTION[ds_upper]
        if destino:
            return {"acao": "MESCLAR", "destino_codigo": destino}

    # Strip-clean matching: remove parenthesized content then retry
    ds_upper_clean = re.sub(r"\s*\([^)]*\)\s*", " ", ds_upper).strip()
    if ds_upper_clean != ds_upper:
        if ds_upper_clean in _LIXO_DUMP:
            return {"acao": "REJEITAR", "motivo": "lixo_ou_metacategoria"}
        if ds_upper_clean in _DUP_DUMP_TO_CONSTITUTION:
            destino = _DUP_DUMP_TO_CONSTITUTION[ds_upper_clean]
            if destino:
                return {"acao": "MESCLAR", "destino_codigo": destino}

    return {
        "acao": "ACEITAR",
        "nome_normalizado": normalizar_nome(ds_tmd or codigo),
    }
