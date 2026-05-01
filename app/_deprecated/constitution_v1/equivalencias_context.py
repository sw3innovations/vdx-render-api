"""
DEPRECATED — context only. NÃO IMPORTAR.

Snapshot do código de seed que populava a tabela `equivalencias` (Constitution DB v1).
A tabela de equivalências cross-fabricante foi substituída pela chave canônica Santa Marina.

Ver: scripts/migrate_constitution_canonical.py para a migração.
Ver: app/_deprecated/constitution_v1/README.md para contexto completo.

Quarentena: 2026-05-01 → remoção prevista: 2026-06-01
"""

# Exemplo de equivalência v1 (schema antigo):
# {
#   "codigo_normalizado": "1101",
#   "fabricante_id": "SM",
#   "codigo_fabricante": "1101SG"
# }
# {
#   "codigo_normalizado": "1101",
#   "fabricante_id": "HE",
#   "codigo_fabricante": "HE 1101A"
# }
# {
#   "codigo_normalizado": "1101",
#   "fabricante_id": "AL",
#   "codigo_fabricante": "1101A"
# }

# No modelo v2, essa relação é expressa por:
# ferragem_canonica.canonical_id = "1101"
# ferragem_canonica.variantes = [
#     {"variant_id": "1101-SM", "fabricante_id": "SM", "codigo_original": "1101SG"},
#     {"variant_id": "1101-HE", "fabricante_id": "HE", "codigo_original": "HE 1101A"},
#     {"variant_id": "1101-AL", "fabricante_id": "AL", "codigo_original": "1101A"},
# ]
