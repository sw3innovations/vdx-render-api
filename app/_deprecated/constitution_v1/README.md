# Constitution DB v1 — Deprecated

**Data de quarentena:** 2026-05-01  
**Motivo:** Refatoração para chave canônica Santa Marina (Sprint refactor/canonical-key-santa-marina)  
**Data prevista de remoção:** 2026-06-01 (30 dias de quarentena)

---

## O que era isso

O modelo v1 usava chaves específicas por fabricante (`SM-1101SG`, `HE-1101A`, `AL-1101A`)
como identificadores primários, com uma tabela de equivalência (`equivalencias`) mantida
manualmente para mapear o mesmo produto entre fabricantes.

### Estrutura v1 (obsoleta)

```python
ferragem = {
    "id": "SM-1101SG",
    "fabricante": "Glasspeças",
    "equivalentes": ["HE-1101A", "AL-1101A"],
    "dimensoes": {...},
    "recorte": {...}
}
```

### Tabelas afetadas

- `ferragens` — tabela original com 1 row por código de fabricante
- `equivalencias` — mapeamento manual cross-fabricante
- `recortes` — recortes por código de fabricante (não por canônico)

---

## Por que foi substituído

Descoberta que os códigos 1101, 1103, 1110 etc. são padrão setorial **Santa Marina
(Linha 1000)** e **Blindex (Linha 3000)**, adotado por TODOS os fabricantes BR com
sufixos próprios. A equivalência cross-fabricante está **embutida no código numérico**,
eliminando a necessidade de tabela manual.

---

## Modelo v2 (atual)

```python
ferragem_canonica = {
    "canonical_id": "1101",           # número puro Santa Marina
    "linha": "santa_marina_1000",
    "categoria": "dobradica",
    "variantes": [
        {"variant_id": "1101-SM", "fabricante": "Glasspeças", ...},
        {"variant_id": "1101-HE", "fabricante": "HELA", ...},
        {"variant_id": "1101-AL", "fabricante": "AL Indústria", ...},
    ]
}
```

O script de migração está em `scripts/migrate_constitution_canonical.py`.

---

## O que NÃO foi movido para cá

As **migrations de banco** (`_m001_fabricantes_ferragens_kits`,
`_m002_recortes_equivalencias`) permanecem em `app/core/constitution.py`.
Elas não podem ser removidas pois são parte da cadeia de upgrade idempotente do schema.
As tabelas `ferragens` e `equivalencias` continuam no banco para compatibilidade e
são a fonte de dados para o script de migração.

---

## O que está neste diretório

- `equivalencias_context.py` — snapshot do código de seed da tabela `equivalencias`
  (context only — não importar em produção)

---

## Quando remover

Após 2026-06-01, se:
1. Nenhum endpoint produção ainda consulta `ferragens` ou `equivalencias` diretamente
2. Constitution DB v2 JSON está validado por Allan
3. ETL pipeline atualizado para carregar variantes completas
