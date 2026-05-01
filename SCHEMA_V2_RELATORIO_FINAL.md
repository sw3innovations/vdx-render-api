# Schema v2 — Relatório Final de Ingestão
**Data:** 2026-05-01  
**Branch:** `feat/schema-v2-ingestao` → merged `main`  
**PR:** [#2](https://github.com/sw3innovations/vdx-render-api/pull/2)

---

## Resumo executivo

| Critério | Status |
|---|---|
| 17/17 códigos vendedora Niedja resolvem via buscar | ✅ |
| 1126, 1128, 1320, 1326 confirmados no DB | ✅ |
| `gv` → `1101R` com confidence=baixo | ✅ |
| `jumbo` em pendentes_validacao_humana | ✅ |
| POST /api/v1/render funcional em produção (401 auth gate) | ✅ |
| Pytest local 678 passed, 7 skipped | ✅ 678 (exigido: 594+) |
| CI GitHub verde | ✅ 36s |
| Deploy produção (VDX port 8001) | ✅ |

---

## DB produção — estado final

| Tabela | Registros |
|---|---|
| `canonicas` | 180 |
| `variantes_canonicas` | 303 |
| `aliases_canonicos` | 15 |
| `kits_canonicos` | 18 |
| `kits_componentes` | 63 |
| `regras_globais` (NBR 7199) | 5 |
| `pendentes_validacao_humana` | 4 |

### Distribuição por linha

| Linha | Canônicos |
|---|---|
| `blindex_3000` | 128 |
| `santa_marina_1000` | 48 |
| `outro` | 4 |

### Distribuição por categoria (top 6)

| Categoria | Canônicos |
|---|---|
| suporte | 62 |
| dobradica | 39 |
| contra_fechadura | 23 |
| trinco | 12 |
| fechadura | 9 |
| puxador | 8 |

---

## 17 códigos da vendedora Niedja — resolução

| Código vendedora | Canonical ID | Tipo resolução | Status |
|---|---|---|---|
| `1101` | 1101 | direto | ✅ |
| `1103` | 1103 | direto | ✅ |
| `114` | 1114 | alias/truncamento | ✅ |
| `1203` | 1203 | direto | ✅ |
| `126D` | 1126 | alias/variant_id | ✅ |
| `128A` | 1128 | alias/variant_id | ✅ |
| `302` | 1302 | alias/truncamento | ✅ |
| `306` | 1306 | alias/truncamento | ✅ |
| `310` | 1310 | alias/truncamento | ✅ |
| `209` | 1209 | alias/truncamento | ✅ |
| `320` | 1320 | alias/truncamento | ✅ |
| `326` | 1326 | alias/truncamento | ✅ |
| `329` | 1329 | alias/truncamento | ✅ |
| `335` | 1335 | alias/truncamento | ✅ |
| `3530` | 3530 | direto | ✅ |
| `510` | 1510 | alias/truncamento | ✅ |
| `520` | 1520 | alias/truncamento | ✅ |

---

## Fases executadas

### Phase 1 — Schema v2 (`_m010_schema_v2`)
9 tabelas novas: `funcoes_canonicas`, `canonicas`, `aliases_canonicos`, `variantes_canonicas`, `alternativas_funcionais`, `kits_canonicos`, `kits_componentes`, `regras_globais`, `pendentes_validacao_humana`.

### Phase 2 — ETL v2 de `ferragens`
Script: `scripts/etl_v2_from_ferragens.py`  
Resultado: 56 canônicos, 162 variantes, 2 junk ignorados (FUSE001, NEWCI001).

### Phase 3 — Ingestão Glasspeças 2022
Script: `scripts/ingestao_glasspecas_2022.py`  
Resultado: 4 canônicos ausentes inseridos (1126, 1128, 1320, 1326), 14 variantes, 5 regras NBR 7199, 18 kits SM, 63 componentes.  
Observação: 8 componentes de kits 17/18 aguardam GMS (inseridos na Phase 4).

### Phase 4 — Ingestão GMS-Blindex
Script: `scripts/ingestao_gms_blindex.py`  
Resultado: 119 canônicos novos (grupos 30–38), 127 variantes GMS.  
Pendentes: LGL e TQ — arquivos não disponíveis no servidor em 2026-05-01.

### Phase 5 — Seed aliases vendedora Niedja
Script: `scripts/seed_aliases_niedja.py`  
Resultado:
- 11 truncamentos (vendedora omite "1" inicial: 114→1114, 302→1302, etc.)
- 3 variant_ids: 126D→1126, 128A→1128, 128B→1128
- 1 apelido comercial: gv→1101R (confidence=baixo, ~55% visual)
- 1 canônico novo: 1101R (Dobradiça Superior Reforçada)
- 2 pendentes: jumbo (não identificado), 1101R (confirmar com catálogo físico)

### Phase 6 — Endpoints v2
Router: `app/routers/ferragens_v2.py` — `/api/v2/ferragens/`  

| Endpoint | Descrição |
|---|---|
| `GET /buscar?q=` | Resolução de alias case-insensitive; 114 → 1114, gv → 1101R |
| `GET /` | Lista canônicos com filtros `linha`, `categoria`, `busca` |
| `GET /filtros` | Valores disponíveis de linha e categoria |
| `GET /{cid}` | Detalhe com aliases + variantes |
| `GET /{cid}/variantes` | Variantes por fabricante |
| `GET /kits` | Lista kits com `?fabricante_origem=`, `?tipologia=` |
| `GET /kits/{kit_id}` | Detalhe do kit com componentes |
| `GET /regras` | Regras globais NBR com `?categoria=` |

v1 endpoints em `/api/v1/canonical/*` inalterados.

### Phase 7 — Validação + deploy
- Ingestion scripts executados em produção via SSH
- Smoke tests: `buscar?q=114` → 1114, `buscar?q=gv` → 1101R confidence=baixo
- POST `/api/v1/render` → 401 (auth gate funcionando)

---

## Pendentes de validação humana

| # | Item | Ação necessária |
|---|---|---|
| 1 | **LGL** — catálogo não disponível | Quando disponível: `scripts/ingestao_lgl.py` |
| 2 | **TQ** — catálogo não disponível | Quando disponível: `scripts/ingestao_tq.py` |
| 3 | **jumbo.jpeg** — ferragem não identificada em 5 catálogos | Perguntar à vendedora Niedja: código exato |
| 4 | **1101R** — identificação a ~55% de confiança | Confirmar com catálogo físico ou com Niedja |

---

## Testes

| Suite | Testes | Status |
|---|---|---|
| `test_schema_v2.py` | 6 | ✅ |
| `test_etl_v2.py` | 11 | ✅ |
| `test_ingestao_glasspecas_2022.py` | 10 | ✅ |
| `test_ingestao_gms.py` | 10 | ✅ |
| `test_seed_aliases_niedja.py` | 10 | ✅ |
| `test_ferragens_v2.py` | 27 | ✅ |
| Demais suites (regressão) | 604 | ✅ |
| **Total** | **678 passed, 7 skipped** | ✅ |

CI GitHub Actions (Python 3.11): ✅ verde em 36s

---

## Notas de arquitetura

**Padrão de truncamento Niedja:** `código_vendedora = canonical_id − 1000` para a faixa 1xxx.  
Exceções (já 4 dígitos, sem alias necessário): 1101, 1103, 1203, 3530.

**GMS 3520 ≠ canonical ferragem na foto gv.jpeg:** O "3520" carimbado na peça é número de lote GMS (Rodízio Excêntrico para Porta de Correr), não código do produto fotografado. Esclarecido durante a análise dos catálogos.

**Resolução de alias case-insensitive:** `LOWER(alias) = LOWER(?)` no SQL garante que `126D`, `126d`, `126D` todos resolvem para `1126`.
