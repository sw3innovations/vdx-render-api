# Migration Report — Constitution DB v2

## Stats
| Métrica | Valor |
|---|---|
| Ferragens legadas lidas | 164 |
| Canônicos gerados | 52 |
| Variantes totais | 157 |
| Órfãs (sem prefixo conhecido) | 7 |
| Conflitos de recorte detectados | 26 |

## Campos stub (a preencher manualmente)
- `recorte_canonico.furos[]` — fonte atual tem apenas `furo_diametro_mm` (escalar); array de furos com x/y requer dado geométrico adicional.
- `recorte_canonico.raios_canto[]` — fonte atual tem apenas `raio_mm` (escalar); array por canto requer geometria adicional.
- `carga_max_kg_nbr16835`, `ciclos_min_nbr16835` — não disponível no catálogo atual.
- `fonte_pdf`, `pagina_pdf` das variantes — maioria `null`; preencher ao importar TQ/LGL.

## Canônicos gerados

- **1001** (santa_marina_1000) · 1 variante(s): AL
- **1002** (santa_marina_1000) · 4 variante(s): AL, AL, AL, HE
- **1003** (santa_marina_1000) · 4 variante(s): AL, AL, HE, HE
- **1005** (santa_marina_1000) · 3 variante(s): AL, AL, HE
- **1013** (santa_marina_1000) · 7 variante(s): AL, AL, AL, HE, HE, HE, SM
- **1038** (santa_marina_1000) · 5 variante(s): AL, AL, AL, HE, HE
- **1101** (santa_marina_1000) · 6 variante(s): AL, AL, HE, HE, SM, SM ⚠️ CONFLITO
- **1103** (santa_marina_1000) · 5 variante(s): AL, AL, HE, HE, SM ⚠️ CONFLITO
- **1114** (santa_marina_1000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **1115** (santa_marina_1000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **1116** (santa_marina_1000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **1123** (santa_marina_1000) · 2 variante(s): AL, HE
- **1125** (santa_marina_1000) · 2 variante(s): AL, AL
- **1130** (santa_marina_1000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **1131** (santa_marina_1000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **1132** (santa_marina_1000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **1201** (santa_marina_1000) · 6 variante(s): AL, AL, HE, HE, SM, SM
- **1203** (santa_marina_1000) · 2 variante(s): AL, HE
- **1209** (santa_marina_1000) · 2 variante(s): AL, HE
- **1230** (santa_marina_1000) · 3 variante(s): AL, AL, HE
- **1231** (santa_marina_1000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **1302** (santa_marina_1000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **1304** (santa_marina_1000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **1306** (santa_marina_1000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **1310** (santa_marina_1000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **1315** (santa_marina_1000) · 1 variante(s): AL
- **1316** (santa_marina_1000) · 2 variante(s): AL, HE
- **1329** (santa_marina_1000) · 3 variante(s): AL, AL, HE
- **1335** (santa_marina_1000) · 4 variante(s): AL, AL, HE, HE
- **1402** (santa_marina_1000) · 1 variante(s): AL
- **1504** (santa_marina_1000) · 5 variante(s): AL, AL, HE, HE, SM
- **1510** (santa_marina_1000) · 11 variante(s): AL, AL, AL, AL, AL, AL, AL, HE, HE, HE, SM ⚠️ CONFLITO
- **1511** (santa_marina_1000) · 6 variante(s): AL, AL, AL, HE, HE, HE
- **1519** (santa_marina_1000) · 1 variante(s): AL
- **1520** (santa_marina_1000) · 4 variante(s): AL, HE, HE, SM ⚠️ CONFLITO
- **1523** (santa_marina_1000) · 2 variante(s): AL, HE
- **1524** (santa_marina_1000) · 1 variante(s): AL
- **1531** (santa_marina_1000) · 2 variante(s): AL, HE
- **1570** (santa_marina_1000) · 4 variante(s): AL, AL, AL, HE
- **1571** (santa_marina_1000) · 4 variante(s): AL, AL, AL, HE
- **1587** (santa_marina_1000) · 1 variante(s): HE
- **1629** (santa_marina_1000) · 7 variante(s): AL, AL, AL, AL, HE, HE, HE
- **1801** (santa_marina_1000) · 2 variante(s): AL, HE
- **3206** (blindex_3000) · 3 variante(s): AL, AL, HE
- **3210** (blindex_3000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **3211** (blindex_3000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **3212** (blindex_3000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **3230** (blindex_3000) · 1 variante(s): HE
- **3530** (blindex_3000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **3532** (blindex_3000) · 4 variante(s): AL, AL, HE, HE ⚠️ CONFLITO
- **3534** (blindex_3000) · 2 variante(s): AL, HE ⚠️ CONFLITO
- **3536** (blindex_3000) · 4 variante(s): AL, AL, HE, HE ⚠️ CONFLITO

## Conflitos detectados (recorte diverge > 5%)

Estes canônicos precisam de revisão humana antes de consolidar recorte:

- `1101` — AL vs SM: comprimento=110.0 vs 110.0
- `1101` — HE vs SM: comprimento=110.0 vs 110.0
- `1103` — AL vs SM: comprimento=125.0 vs 125.0
- `1103` — HE vs SM: comprimento=125.0 vs 125.0
- `1114` — AL vs HE: comprimento=50.0 vs 50.0
- `1115` — AL vs HE: comprimento=50.0 vs 50.0
- `1116` — AL vs HE: comprimento=62.0 vs 76.0
- `1130` — AL vs HE: comprimento=50.0 vs 110.0
- `1131` — AL vs HE: comprimento=40.0 vs None
- `1132` — AL vs HE: comprimento=76.0 vs 105.0
- `1231` — AL vs HE: comprimento=50.0 vs 110.0
- `1302` — AL vs HE: comprimento=38.0 vs 50.0
- `1304` — AL vs HE: comprimento=50.0 vs 110.0
- `1306` — AL vs HE: comprimento=50.0 vs 110.0
- `1310` — AL vs HE: comprimento=50.0 vs 27.0
- `1510` — AL vs SM: comprimento=120.0 vs 120.0
- `1510` — HE vs SM: comprimento=120.0 vs 120.0
- `1520` — AL vs SM: comprimento=75.0 vs 73.0
- `1520` — HE vs SM: comprimento=75.0 vs 73.0
- `3210` — AL vs HE: comprimento=85.0 vs 84.0
- `3211` — AL vs HE: comprimento=85.0 vs 84.0
- `3212` — AL vs HE: comprimento=85.0 vs 84.0
- `3530` — AL vs HE: comprimento=85.0 vs 84.0
- `3532` — AL vs HE: comprimento=None vs 84.0
- `3534` — AL vs HE: comprimento=85.0 vs 84.0
- `3536` — AL vs HE: comprimento=None vs 84.0

## Ferragens órfãs (sem prefixo conhecido — revisão manual necessária)

- `FUSE001` (codigo_normalizado=`FUSE001`, fab=`SM`)
- `NEWCI001` (codigo_normalizado=`NEWCI001`, fab=`SM`)
- `PUXADOR 115` (codigo_normalizado=`PUXADOR 115`, fab=`HE`)
- `PUXADOR 200` (codigo_normalizado=`PUXADOR 200`, fab=`HE`)
- `PUXADOR 300` (codigo_normalizado=`PUXADOR 300`, fab=`HE`)
- `PUXADOR 400` (codigo_normalizado=`PUXADOR 400`, fab=`HE`)
- `PUXADOR 400` (codigo_normalizado=`PUXADOR 400`, fab=`SM`)
