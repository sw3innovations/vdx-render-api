"""Limites físicos do domínio VDX (vidro temperado).

Fonte: NBR 7199 + especificações de fabricantes (HELA, AL Indústria, Glasspeças).
Todos os limites em milímetros, exceto QUANTIDADE_MAX_ITEM.
"""

# Dimensões de peças de vidro
DIMENSAO_MIN_MM = 100       # menor peça razoável (pequeno fixo / bandeira)
DIMENSAO_MAX_MM = 6000      # maior chapa de vidro temperado disponível no mercado

# Espessuras comerciais de vidro temperado
ESPESSURA_MIN_MM = 4
ESPESSURA_MAX_MM = 25

# Proposta comercial
QUANTIDADE_MAX_ITEM = 999   # sanity check — ninguém pede 999 portas iguais
