# Confronto: Ferragens da Vendedora × Catálogos
**Data:** 2026-05-01  
**Fonte fotos:** `/home/sw3innovation/ferragens_vendedora/` (22 arquivos)  
**Fontes catálogo:** Glasspeças 2017 (local), Glasspeças 2022 (baixado), AL cat, HE cat  
**DB:** `data/constitution.db` — somente leitura

---

## Resumo executivo

| Métrica | Valor |
|---|---|
| Total arquivos da vendedora | 22 |
| Arquivos com código numérico | 17 |
| Arquivos descritivos (sem código) | 5 |
| Canonical IDs extraídos | 19 únicos ¹ |
| Presentes em `ferragens` (origem) | 13 / 19 (68%) |
| Presentes em `ferragens_canonicas` | 13 / 19 (68%) |
| **Ausentes do DB inteiro (apenas em catálogo)** | **4** (`1126`, `1128`, `1320`, `1326`) |
| Silenciados (origem mas não canônico) | 0 — todos os 13 DB-residentes já estão no canônico |
| Truncamentos confirmados (3-dígito → 4-dígito) | **11** |
| Descritivos categorizados | 4 / 5 |
| Descritivos pendentes | 1 (`jumbo`) |

> ¹ O arquivo `310 + 209 facao.jpeg` contém dois códigos (`1310` + `1209`). `320` aparece em dois arquivos. Total distinto = 19 canonical IDs.

---

## Tabela de confronto — 22 entradas

| Arquivo vendedora | Cód. vendedora | Canonical_ID | DB origem | DB canônico | Glasspeças 17 | Glasspeças 22 | AL cat | HE cat | Hipótese |
|---|---|---|---|---|---|---|---|---|---|
| 1101.jpeg | `1101` | **1101** | ✅ SM+HE+AL | ✅ | ✅ | ✅ | ✅ | ❌ ² | Canônico SM, multi-fab |
| 1103.jpeg | `1103` | **1103** | ✅ SM+HE+AL | ✅ | ✅ | ✅ | ✅ | ✅ | Canônico SM, multi-fab |
| 114.jpeg | `114` | **1114** | ✅ AL+HE | ✅ | ✅ 1114 | ✅ 1114 | ✅ 1114 | ❌ | TRUNCAMENTO `114→1114` |
| 1203.jpeg | `1203` | **1203** | ✅ HE+AL | ✅ | ✅ | ✅ | ✅ | ✅ | Canônico SM, multi-fab |
| 126 D.jpeg | `126D` | **1126** | ❌ | ❌ | ✅ `1126, 126D, 126C...` | ✅ 1126 (carrinho correr) | ❌ | ❌ | `126D` = variante do 1126 ³, **ausente DB** |
| 128A 128B.jpeg | `128A/128B` | **1128** | ❌ | ❌ | ✅ `1128A, 128B` | ❌ | ❌ | ❌ | TRUNCAMENTO `128→1128`, **ausente DB** |
| 302.jpeg | `302` | **1302** | ✅ AL+HE | ✅ | ✅ 1302 | ✅ 1302 | ❌ | ✅ | TRUNCAMENTO `302→1302` |
| 306.jpeg | `306` | **1306** | ✅ AL+HE | ✅ | ✅ 1306 | ✅ 1306 | ❌ | ❌ | TRUNCAMENTO `306→1306` |
| 310 + 209 facao.jpeg | `310` + `209` | **1310** + **1209** | ✅ ambos AL+HE | ✅ ambos | ✅ | ✅ | ❌ | ✅ | Foto composta — 2 ferragens + "facão" = descriptor aplicação ⁴ |
| 310.jpeg | `310` | **1310** | ✅ AL+HE | ✅ | ✅ 1310 | ✅ 1310 | ❌ | ✅ | TRUNCAMENTO `310→1310` |
| 320 colante e 320 passante.jpeg | `320` | **1320** | ❌ | ❌ | ✅ 1320 | ✅ `1320 G` (Suporte) | ❌ | ✅ 320 | TRUNCAMENTO `320→1320`, **ausente DB** |
| 326 mini.jpeg | `326` | **1326** | ❌ | ❌ | ✅ 1326 | ✅ `1326 G` (Suporte Fixação Vidro) | ❌ | ❌ | TRUNCAMENTO `326→1326`, **ausente DB** |
| 329.jpeg | `329` | **1329** | ✅ AL+HE | ✅ | ✅ 1329 | ✅ | ❌ | ✅ | TRUNCAMENTO `329→1329` |
| 335 porta de correr porta de giro.jpeg | `335` | **1335** | ✅ AL+HE | ✅ | ✅ 1335 | ✅ | ✅ | ✅ | TRUNCAMENTO `335→1335` |
| 3530.jpeg | `3530` | **3530** | ✅ AL+HE | ✅ | ✅ (espelho fech.) | ✅ | ❌ | ❌ | Canônico Blindex 3000 |
| 510.jpeg | `510` | **1510** | ✅ SM+HE+AL | ✅ | ✅ 1510 | ✅ | ❌ | ✅ | TRUNCAMENTO `510→1510` |
| 520.jpeg | `520` | **1520** | ✅ SM+HE+AL | ✅ | ✅ 1520 | ✅ | ✅ | ❌ | TRUNCAMENTO `520→1520` |
| box articulado.jpeg | descritivo | — | — | — | ✅ "porta camarão articulada" | ✅ | ❌ | ❌ | **Sistema**, não ferragem isolada |
| furo para puxador.jpeg | descritivo | — | — | — | ✅ gabarito recorte | ✅ | ❌ | ❌ | **Gabarito de recorte**, não ferragem |
| gv.jpeg | `GV` (apelido) | **1101R** (hipótese) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **DOBRADIÇA REFORÇADA** ~55% conf. Carimbo "3520" = lote GMS (não código). Pendente confirmação ⁶ |
| jumbo.jpeg | descritivo | — | — | — | ❌ | ❌ | ❌ | ❌ | **NÃO IDENTIFICADO** — pendente confirmação vendedora ⁵ |
| max system.jpeg | descritivo | — | — | — | ✅ "maxim-ar" | ✅ "Max-Ar V.V." | ❌ | ❌ | **Sistema maxim-ar** (ventilação), não ferragem isolada |

> ² HE 1101 existe em `ferragens` mas o catálogo HE local (PDF) não apareceu na busca — possível extração incompleta do PDF, não ausência real.  
> ³ Glasspeças 2017 lista explicitamente: `"1126, 126D, 126C, 126DC e 1126QC"` na mesma família. `126D` é o variant_id dentro do canônico `1126`, não um canonical separado.  
> ⁴ "facão" = modo de aplicação (chanfro/fação). Não é código de ferragem.  
> ⁵ "Jumbo" não aparece em nenhum catálogo pesquisado. Hipóteses: (a) apelido informal para 1101/1103 em tamanho extra-large; (b) ferragem de marca própria não catalogada; (c) sistema de box com dobradiça jumbo (ex: box 8mm folha grande).
> ⁶ Reidentificado em 2026-05-01: peça da foto é dobradiça zamac reforçada com 3 furos (castelinhos) no topo, recorte em C no corpo, furo circular inferior. Melhor candidato: 1101R (Dobradiça Superior Reforçada). O "3520" carimbado é número de lote GMS-Blindex (= Rodízio Excêntrico para Porta de Correr), não código do produto. Alias `gv → 1101R` seed em Phase 5 com confidence=baixo. Pendente: confirmar com vendedora ou catálogo físico.

---

## Truncamentos confirmados (11 pares)

A vendedora usa sistematicamente o código sem o "1" inicial. Todos confirmados em ≥2 fontes independentes.

| Código vendedora | Canonical_ID | Fontes confirmadoras | DB presente? |
|---|---|---|---|
| `114` | `1114` | Glasspeças 2017+2022, AL cat | ✅ |
| `302` | `1302` | Glasspeças 2017+2022, HE cat, DB | ✅ |
| `306` | `1306` | Glasspeças 2017+2022, DB | ✅ |
| `310` | `1310` | Glasspeças 2017+2022, HE cat, DB | ✅ |
| `209` (no composto) | `1209` | Glasspeças 2017+2022, AL+HE cat, DB | ✅ |
| `320` | `1320` | Glasspeças 2017+2022, HE cat | ❌ ausente DB |
| `326` | `1326` | Glasspeças 2017+2022 | ❌ ausente DB |
| `329` | `1329` | Glasspeças 2017+2022, HE cat, DB | ✅ |
| `335` | `1335` | Glasspeças 2017+2022, AL+HE cat, DB | ✅ |
| `510` | `1510` | Glasspeças 2017+2022, HE cat, DB | ✅ |
| `520` | `1520` | Glasspeças 2017+2022, AL cat, DB | ✅ |

**Padrão:** `código_vendedora = canonical_id - 1000` (quando canonical_id está na faixa 1000–1999).  
**Exceções:** códigos `1101`, `1103`, `1203` — 4 dígitos, a vendedora já usa o código completo.

---

## Ausentes do DB inteiro (4 canonical IDs prioritários)

Estes códigos existem nos catálogos e a vendedora os usa, mas **não estão em `ferragens` nem em `ferragens_canonicas`**:

| Canonical_ID | Produto (Glasspeças) | Ano catálogo | DB origem | DB canônico |
|---|---|---|---|---|
| `1126` | Carrinho para Porta de Correr | 2017 + 2022 | ❌ | ❌ |
| `1128` | Dobradiça/Articulação 1128 A/B/C | 2017 apenas | ❌ | ❌ |
| `1320` | Suporte sem Miolo 1320 G | 2017 + 2022 | ❌ | ❌ |
| `1326` | Suporte para Fixação de Vidro 1326 G | 2017 + 2022 | ❌ | ❌ |

Estes 4 precisam ser ingeridos do Glasspeças 2022 antes de qualquer deploy para a vendedora.

---

## Categorias/sistemas (não-ferragem isolada)

| Arquivo | Identificação | Decisão de schema |
|---|---|---|
| `box articulado.jpeg` | Porta camarão articulada (conjunto multi-ferragem, Glasspeças p. ~5826) | Tag `familia=box_articulado` — não cria canonical_id |
| `furo para puxador.jpeg` | Gabarito de recorte para puxador | Entra como `recorte`, não como `ferragem` |
| `gv.jpeg` | Puxador GV Zamac cromado (GLASSVETRO `01.35.860`/`01.35.861`) | **Já em `ferragens_canonicas`** — nenhuma ação necessária |
| `max system.jpeg` | Sistema maxim-ar com haste (Glasspeças "Maxim-Ar V.V.") | Tag `familia=max_ar` — não cria canonical_id |
| `jumbo.jpeg` | **NÃO IDENTIFICADO** | Pendente: vendedora deve confirmar marca/código |

---

## Padrões de código encontrados

| Padrão | Qtd. arquivos | Exemplos | Status schema v2 |
|---|---|---|---|
| `4 dígitos completos` | 4 arquivos | 1101, 1103, 1203, 3530 | canonical_id direto |
| `3 dígitos = 1xxx truncado` | 11 arquivos | 510→1510, 302→1302, 114→1114 | alias[] no canonical |
| `4 dígitos ausentes do DB` | 2 arquivos | 1126 (via 126D), 1128 | ingestão pendente |
| `Truncados ausentes do DB` | 2 arquivos | 320→1320, 326→1326 | ingestão pendente |
| `GV (marca)` | 1 arquivo | gv→Puxador GV GLASSVETRO | já no canonical |
| `Descritivo de sistema` | 3 arquivos | box articulado, max system | familia/tag, não canonical |
| `Gabarito` | 1 arquivo | furo para puxador | recorte, não ferragem |
| `Não identificado` | 1 arquivo | jumbo | pendente |

---

## Recomendações para schema v2

**1. Campo `aliases[]` no canonical obrigatório**  
11 dos 22 arquivos usam truncamentos. A vendedora nunca vai digitar `1510` — vai digitar `510`. O schema v2 precisa de um array de aliases por canonical_id, pre-populado com o truncamento 3-dígito (quando aplicável):
```json
{ "canonical_id": "1510", "aliases": ["510"] }
{ "canonical_id": "1302", "aliases": ["302"] }
```

**2. Variante `126D` ≠ truncamento simples**  
`126D` é `variant_id` dentro do canonical `1126`, não "1" + "126D". O campo `aliases[]` precisa aceitar variant_ids também, não só canonical_ids.

**3. Os 4 ausentes são prioritários para ingestão**  
- `1126` e `1320` e `1326` estão na Glasspeças 2022 (já baixada em `/tmp/glasspecas_2022.pdf`).  
- `1128` está só na Glasspeças 2017 — considerar se ainda é produto ativo.  
- Ingestão destes 4 ANTES de qualquer deploy para a vendedora.

**4. GMS-Blindex indisponível para download**  
URL fornecida retornou erro. Sem dados para confirmar `3530` no Blindex. Não é bloqueante — `3530` já está no DB via AL+HE.

**5. `jumbo` precisa de confirmação humana**  
Não encontrado em nenhum dos 5 catálogos pesquisados. Antes de criar schema, perguntar à vendedora: código exato ou apelido informal?
