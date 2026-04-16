# VDX Glass Engine — Arquitetura Completa

> Documento gerado em 2026-04-15 a partir do estado real do repositório.  
> Um dev novo deve conseguir entender o projeto inteiro lendo só este arquivo.

---

## 1. Visão Geral

**VDX Glass Engine** é uma API REST que recebe o nome de uma tipologia de vidraçaria (ex: `porta_pivotante_simples`) + dimensões de peças e retorna desenho técnico SVG, PNG, PDF, thumbnail e Scene JSON para viewer 3D interativo.

| Item | Valor |
|---|---|
| Linguagem | Python 3.14.3 |
| Framework | FastAPI 0.115.0 |
| DB | SQLite 3 (WAL mode) |
| Server (prod) | uvicorn, porta 8001, systemd `vdx-render` |
| Deploy | GitHub Actions → rsync → VPS → systemctl restart |
| Repo | https://github.com/sw3innovations/vdx-render-api |
| Branches ativas | `main` (prod), `feature/image-generator`, `feature/preview-highlight`, `feature/sync-banco-auto-generate`, `fix/add-missing-tipologias` |
| Docs interativos | `/docs` (Swagger), `/redoc` |
| Health check | `GET /health` → `{"status":"ok","versao":"1.0.0"}` |

### Stack resumida

```
HTTP Request
    ↓
FastAPI (uvicorn) + slowapi (rate limit)
    ↓
render_orchestrator.py   ← orquestra tudo
    ├─ normalizer.py      ← resolve alias → tipologia canônica
    ├─ constitution_engine.py ← busca ferragens + posiciona
    ├─ abnt_validator.py  ← verifica folgas NBR
    ├─ svg_template_engine.py ← gera SVG
    └─ scene_builder.py   ← gera Scene JSON 3D
         ↓                    ↓
    conversion_service.py   viewer_3d.py (HTML)
    (PNG / PDF / thumb)
```

---

## 2. Estrutura de Diretórios

```
vdx-render-api/
│
├── app/                          # código principal
│   ├── main.py                   # entrypoint FastAPI (53L)
│   │
│   ├── core/                     # conhecimento + infra
│   │   ├── abnt_validator.py     # validação NBR (180L)
│   │   ├── constitution.py       # Constitution DB API (549L)
│   │   ├── constitution_seed.py  # seed de tipologias (681L)
│   │   ├── limiter.py            # rate limiter config (4L)
│   │   └── normalizer.py         # normalizador inteligente (166L)
│   │
│   ├── models/
│   │   ├── feedback.py           # FeedbackRequest/Response (21L)
│   │   └── render.py             # todos os Pydantic models (140L)
│   │
│   ├── renderers/
│   │   ├── scene_builder.py      # RenderResponse → Scene JSON 3D (350L)
│   │   └── svg_template_engine.py# RenderResponse → SVG (511L)
│   │
│   ├── routers/
│   │   ├── chat.py               # POST /api/v1/chat (162L)
│   │   ├── export.py             # PNG/PDF/thumb endpoints (161L)
│   │   ├── feedback.py           # POST /api/v1/feedback (25L)
│   │   ├── preview.py            # GET tipologia preview (71L)
│   │   ├── render.py             # POST /api/v1/render (38L)
│   │   ├── tipologia_image.py    # GET tipologia image (57L)
│   │   ├── tipologia_sync.py     # POST tipologia/sync (79L)
│   │   └── viewer_3d.py          # 3D JSON + HTML viewer (531L)
│   │
│   ├── services/
│   │   ├── claude_teacher.py     # Claude resolve tipologias novas (163L)
│   │   ├── constitution_engine.py# motor de consulta à Constitution (355L)
│   │   ├── conversion_service.py # SVG → PNG/PDF/thumbnail (42L)
│   │   ├── feedback_service.py   # aplica correções do vidraceiro (102L)
│   │   ├── image_generator.py    # gera imagem realista via SD 1.5 (132L)
│   │   ├── preview_generator.py  # gera e cacheia preview SVG (383L)
│   │   ├── render_orchestrator.py# pipeline principal (234L)
│   │   ├── render_validator.py   # Claude valida posicionamento (172L)
│   │   └── svg_service.py        # SVG legado/alternativo (527L)
│   │
│   └── _deprecated/              # módulos antigos — não deletar (referência)
│       ├── catalogo.py           # (160L) - resolver_layout_por_nome
│       ├── classificador.py      # (53L)  - classificar_peca legado
│       ├── claude_service.py     # (126L) - claude legado
│       ├── constitution_seed.py  # (612L) - seed original
│       ├── kit_resolver.py       # (156L) - resolver_kit legado
│       ├── posicionamento_service.py # (152L) - posicionamento legado
│       └── skill_vidracaria.py   # (2086L) - skill original monolítica
│
├── data/
│   ├── constitution.db           # SQLite DB principal (272KB, WAL)
│   ├── catalogs/
│   │   ├── catalogo_hela.json    # catálogo HELA (57KB, 158 ferragens)
│   │   └── catalogo_al_industria.json # catálogo AL (52KB)
│   └── outputs/                  # PNGs/PDFs gerados (gitignored)
│
├── tests/
│   ├── test_constitution_catalog.py  # testes Sprint 1 (541L)
│   ├── test_svg_engine.py            # testes Sprint 2 (393L)
│   └── test_scene_builder.py         # testes Sprint 4 (303L)
│
├── tools/
│   └── catalog_loader.py         # popula Constitution DB dos JSONs
│
├── scripts/
│   └── generate_image.py         # CLI para gerar imagem via SD 1.5
│
├── Dockerfile                    # python:3.12-slim, porta 8000
├── requirements.txt              # deps completas (+ cairosvg, Pillow)
├── requirements_prod.txt         # deps mínimas (sem cairosvg, Pillow)
├── .env                          # ANTHROPIC_API_KEY, VDX_API_MASTER_KEY, PORT
├── .github/workflows/deploy.yml  # CI/CD: push main → rsync VPS → systemctl
└── README.md
```

---

## 3. Módulos por Sprint

### Sprint 0 — Catálogos (ferramentas offline)

**`tools/catalog_loader.py`** — Popula Constitution DB a partir dos JSONs dos fabricantes.
```bash
python -m tools.catalog_loader               # carrega todos
python -m tools.catalog_loader --fabricante HE
python -m tools.catalog_loader --dry-run
python -m tools.catalog_loader --stats
```
Fontes: `data/catalogs/catalogo_hela.json` (HELA), `data/catalogs/catalogo_al_industria.json` (AL Indústria). Popula `fabricantes`, `ferragens`, `kits`, `kit_componentes`, `recortes`, `equivalencias`.

---

### Sprint 1 — Constitution DB

**`app/core/constitution.py`** (549L) — API completa sobre SQLite.

Funções públicas:
| Função | O que faz |
|---|---|
| `init_db()` | DDL: cria tabelas + chama `migrate()`. Nunca popula dados. |
| `migrate()` | Migrações idempotentes de schema. |
| `buscar(nicho, tipo, chave)` | Busca entry na constitution. |
| `registrar(nicho, tipo, chave, dados)` | Upsert de entry. |
| `normalizar(nicho, alias, tipo)` | Resolve alias → canonical. |
| `registrar_alias(...)` | Adiciona alias. |
| `buscar_ferragem(codigo)` | Busca por código (qualquer formato). |
| `buscar_kit(numero, fabricante_id)` | Busca kit completo. |
| `buscar_recortes(ferragem_codigo)` | Recortes necessários para uma ferragem. |
| `buscar_equivalentes(codigo)` | Equivalências cross-fabricante. |
| `buscar_folga_nbr(tipo)` | Folga NBR em mm. Ex: `'movel_fixo'` → 3.0 |
| `get_stats()` | Contagem de rows por tabela. |

**`app/core/constitution_seed.py`** (681L) — Dados de tipologias VDX.

`seed()` — registra 22 tipologias + 113 aliases. Idempotente (INSERT OR REPLACE). Assume que `init_db()` já rodou. Nunca chama `init_db()`.

Tipologias registradas:

| Chave | Layout | Classes de peça | Ferragens/peca |
|---|---|---|---|
| `porta_pivotante_simples` | paralelas | movel | 3 (dobradicas + fechadura) |
| `porta_correr_2_folhas` | paralelas | correr | 3 (roldanas + guia) |
| `porta_correr_3_folhas` | paralelas | correr | 3 |
| `porta_pivotante_dupla_bandeira` | bandeira_topo | movel | 3 |
| `box_banheiro` | paralelas | movel | 4 (pivo + puxador) |
| `box_para_banheiro` | paralelas | movel | 4 |
| `box_frontal_2_folhas` | paralelas | movel | 2 |
| `box_canto_90` | paralelas | movel | 2 |
| `box_de_giro` | paralelas | movel | 2 |
| `janela_basculante` | basculante | movel | 2 |
| `janela_correr_2_folhas` | paralelas | correr | 3 |
| `janela_correr_2_folhas_oriun_plus` | paralelas | correr | 3 |
| `janela_maxim_ar` | paralelas | movel | 3 |
| `janela_pivotante` | paralelas | movel | 3 |
| `janela_quatro_folhas` | paralelas | correr | 3 |
| `fechamento_de_sacada_6_folhas` | paralelas | correr | 2 |
| `guarda_corpo_linear` | paralelas | — | 0 |
| `divisoria_porta_pivotante` | paralelas | movel | 3 |
| `cobertura` | paralelas | — | 0 |
| `porta` | paralelas | movel/correr | 3 |
| `porta_abrir` | paralelas | movel | 3 |
| `vitrine` | paralelas | movel | 3 |

**`app/core/normalizer.py`** (166L) — Normalizador Inteligente em 3 camadas.

```
classificar_peca(nome) → "fixa" | "movel" | "correr"
  Camada 1: match exato em aliases (constitution_aliases tipo=classificacao_peca)
  Camada 2: match por tokens (split + heurística)
  Camada 3: default "fixa" + warning

normalizar_tipologia(nome) → chave canônica
  Camada 1: match exato em aliases (tipo=tipologia)
  Camada 2: fuzzy por tokens
  Camada 3: None (desconhecida)
```

**`app/core/abnt_validator.py`** (180L) — Validação NBR.

```
ABNTValidator.verificar(pecas, vao) → lista de alertas
```
Folgas NBR em `folgas_nbr`:
- `movel_fixo`: 3mm
- `movel_movel`: 4mm
- `movel_piso`: 8mm
- `fixo_fixo`: 1mm
- `movel_alvenaria`: 5mm

---

### Sprint 2 — SVG Engine + Render Pipeline

**`app/services/render_orchestrator.py`** (234L) — Ponto de entrada do pipeline.

```python
await executar(RenderRequest) → RenderResponse
```

Três modos (em ordem de prioridade):
1. **`constitution`** — tipologia encontrada no DB → `ConstitutionEngine` → ferragens posicionadas
2. **`claude_teacher`** — tipologia desconhecida + `ANTHROPIC_API_KEY` disponível → Claude resolve e registra na Constitution para a próxima vez
3. **`fallback`** — sem chave Anthropic → módulos legados `_deprecated/`

**`app/services/constitution_engine.py`** (355L) — Motor de consulta.

```python
ConstitutionEngine.resolver_tipologia(tipologia_nome) → dict  # dados da tipologia
classificar_peca(nome, dados_tipologia) → "fixa"|"movel"|"correr"
posicionar_ferragens(peca, classificacao, dados_tipologia) → [FerragemPosicionada]
resolver_kit(tipologia_nome) → KitFerragem | None
montar_regras_interativas(dados) → RegrasInterativas
enriquecer_ferragem_com_catalogo(blueprint) → FerragemEnriquecida
```

Fórmulas de posição (avaliadas com `eval` sandboxado — `{"__builtins__": {}}`):
- Variáveis disponíveis: `largura`, `altura`, `comprimento`, `espessura`
- Exemplos: `"altura - 50"`, `"largura * 0.50"`, `"15"`

**`app/renderers/svg_template_engine.py`** (511L) — Gerador de SVG.

```python
SVGTemplateEngine.gerar_svg(resp: RenderResponse, tema, opcoes) → str (SVG)
```
- Escala automática para caber em viewport
- Labels de ferragens com anti-colisão vertical
- Destaque de peça (server-side highlight)
- Convenção de cores por tipo de ferragem

**`app/services/svg_service.py`** (527L) — Serviço SVG alternativo (legado).

**`app/services/claude_teacher.py`** (163L) — Claude como fallback inteligente.

```python
resolver_tipologia_desconhecida(nome, pecas) → dados_tipologia
```
Quando a Constitution não conhece a tipologia, Claude analisa o nome e as peças, infere ferragens prováveis, e registra o resultado na Constitution para aprendizado contínuo.

**`app/services/render_validator.py`** (172L) — Claude valida posicionamento pós-render.

**`app/models/render.py`** (140L) — Todos os tipos Pydantic:

```python
# Input
class PecaInput(nome, largura_mm, altura_mm, fabricante_id?)
class RenderRequest(tipologia_nome, pecas, formato, tema, opcoes?)

# Output
class FerragemPosicionada(nome, codigo, tipo, x_mm, y_mm, lado, recorte, classificacao_peca)
class PecaRenderizada(nome, largura_mm, altura_mm, ferragens, classificacao)
class RenderResponse(svg, pecas, metadata, alertas_abnt, modo, confianca)

# Enums
class Formato: svg | png | pdf
class Layout: paralelas | basculante | bandeira_topo | ...
class Tema: claro | escuro | blueprint
```

---

### Sprint 3 — Export (PNG / PDF / Thumbnail)

**`app/services/conversion_service.py`** (42L) — Conversor SVG.

```python
svg_para_png(svg: str, scale=2.0) → bytes     # CairoSVG, retina-ready
svg_para_pdf(svg: str) → bytes                # CairoSVG
svg_para_thumbnail(svg: str, 240, 180) → bytes # Pillow + preserva aspect ratio
```

**`app/routers/export.py`** (161L) — 5 endpoints de exportação (ver seção 4).

Rate limit: `@limiter.limit("5/second")` para PNG/PDF, `10/second` para thumbnail.

---

### Sprint 4 — 3D Interativo

**`app/renderers/scene_builder.py`** (350L) — Converte `RenderResponse` em Scene JSON versionado para o Three.js viewer.

```python
SceneBuilder.build(resp, espessura_vidro=8.0, cor_vidro="default") → dict
```

**Coordenadas:**
- `y_3d = y_mm` (direto — ConstitutionEngine já mede da base para cima)
- `x_3d`: centrado em 0 usando `center_x = total_largura / 2`
- `z_3d = ±(espessura/2 + profundidade_ferragem/2)` (ferragens na face do vidro)

**Layouts suportados:**
- `paralelas` / `fixo_movel_fixo`: peças lado a lado (x acumula)
- `bandeira_topo`: peça menor no topo, restante abaixo (y com offset)
- `basculante`: peças empilhadas verticalmente (y acumula)

**Materiais PBR (MATERIAIS_PBR):**

| Material | Cor | Roughness | Metalness |
|---|---|---|---|
| cromado | #C0C0C0 | 0.15 | 0.95 |
| inox | #D4D4D4 | 0.20 | 0.90 |
| preto | #1A1A1A | 0.40 | 0.30 |
| branco | #F5F5F5 | 0.50 | 0.00 |
| bronze | #8B6914 | 0.30 | 0.70 |
| dourado | #D4AF37 | 0.20 | 0.85 |
| fosco | #A0A0A0 | 0.60 | 0.50 |

**Cores de vidro (CORES_VIDRO):**

| Cor | Hex | Opacidade | Metalness |
|---|---|---|---|
| incolor | #E8F4F8 | 0.25 | — |
| verde | #88CCAA | 0.30 | — |
| fume | #444444 | 0.45 | — |
| bronze | #AA8855 | 0.35 | — |
| espelho | #C8D8E8 | 0.15 | 0.85 |
| default | #B8D4E3 | 0.25 | — |

**Animações por tipologia:**

| Keyword na chave | Tipo | Eixo | Parâmetro |
|---|---|---|---|
| `pivotante`, `abrir` | pivotante | y | angulo_max=90 |
| `vai_vem`, `vaivem` | pivotante | y | angulo_min=-90 |
| `correr`, `box`, `sacada` | deslizante | x | distancia_max=largura |
| `basculante` | basculante | x | angulo_max=45 |
| `maxim` | basculante | x | angulo_max=60 |

**`app/routers/viewer_3d.py`** (531L) — Dois endpoints:

1. `POST /api/v1/render/export/3d` → Scene JSON
2. `GET /api/v1/3d/viewer` → HTML autossuficiente com Three.js r128 embutido

O HTML inclui:
- Three.js r128 via jsDelivr CDN
- OrbitControls (script separado, injeta em `THREE.OrbitControls`)
- Cena embedded como `const SCENE = {...}` (não `SCENE_DATA`)
- 3-point studio lighting (key/fill/rim + ambient)
- Glass: `MeshPhysicalMaterial` (transmission=0.8, ior=1.52, depthWrite=false)
- Hardware: `MeshStandardMaterial` (metalness/roughness por tipo)
- Parede/vão: 3 boxes (pilar esq, pilar dir, verga)
- UI: botão abrir/fechar, 6 swatches de cor, reset câmera, screenshot
- Screenshot: `canvas.toBlob` → `<a>` download (requer `preserveDrawingBuffer: true`)

---

## 4. Endpoints

| Método | Path | Sprint | Rate Limit | Auth | Descrição |
|---|---|---|---|---|---|
| GET | `/health` | S1 | — | — | Health check |
| GET | `/docs` | — | — | — | Swagger UI |
| GET | `/redoc` | — | — | — | ReDoc |
| POST | `/api/v1/render` | S2 | 10/s | VDX-Key | SVG + ferragens + alertas ABNT |
| POST | `/api/v1/render/export/png` | S3 | 5/s | VDX-Key | PNG binário (scale=2.0) |
| POST | `/api/v1/render/export/pdf` | S3 | 5/s | VDX-Key | PDF binário |
| POST | `/api/v1/render/export/thumbnail` | S3 | 10/s | VDX-Key | PNG thumbnail (240×180) |
| POST | `/api/v1/render/export/3d` | S4 | 5/s | VDX-Key | Scene JSON versionado |
| GET | `/api/v1/3d/viewer` | S4 | — | key= | HTML Three.js viewer |
| POST | `/api/v1/chat` | S2 | — | — | Consultor técnico (Claude) |
| POST | `/api/v1/feedback` | S2 | — | — | Feedback do vidraceiro |
| POST | `/api/v1/tipologia/sync` | S2 | — | — | Sync tipologia → Constitution |
| GET | `/api/v1/tipologia/{chave}/preview` | S2 | — | — | Preview SVG animado |
| GET | `/api/v1/tipologia/{chave}/preview/png` | S3 | — | — | Preview como PNG |
| GET | `/api/v1/tipologia/{chave}/preview/thumbnail` | S3 | — | — | Preview como thumbnail |
| GET | `/api/v1/tipologia/{chave}/image` | S2 | — | — | Imagem realista (SD 1.5) |
| POST | `/api/v1/tipologias/images/gerar-todas` | S2 | — | VDX-Key | Gera imagens de todas |
| GET | `/api/v1/tipologias/previews` | S2 | — | — | Lista todos os previews |
| POST | `/api/v1/tipologias/previews/regenerar` | S2 | — | VDX-Key | Regenera todos previews |

**Auth:** Header `X-VDX-Key: <VDX_API_MASTER_KEY>` ou query param `key=`. Ausente → 401.

---

## 5. Constitution DB Schema

### Tabelas

#### `constitution_entries` — Knowledge base de tipologias
```sql
CREATE TABLE constitution_entries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nicho         TEXT NOT NULL DEFAULT 'vidros',
    tipo          TEXT NOT NULL,          -- 'tipologia' | 'preview'
    chave         TEXT NOT NULL,          -- ex: 'porta_pivotante_simples'
    dados         TEXT NOT NULL,          -- JSON com ferragens_por_peca, layout, etc.
    origem        TEXT NOT NULL DEFAULT 'seed',
    confianca     REAL NOT NULL DEFAULT 1.0,
    validado_por  TEXT,
    versao        TEXT NOT NULL DEFAULT '2026.03.20',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(nicho, tipo, chave)
);
CREATE INDEX idx_entries_chave ON constitution_entries(nicho, tipo, chave);
```

Estrutura do JSON `dados` para tipo=`tipologia`:
```json
{
  "layout_padrao": "paralelas",
  "ferragens_por_peca": {
    "movel": [
      {"codigo": "1101", "nome": "Dobradiça Superior", "tipo": "dobradica",
       "y_formula": "altura - 50", "x_formula": "15", "lado": "esquerdo",
       "visual": "retangulo", "recorte": "padrao_sm"}
    ],
    "puxador_config": {"y_formula": "altura * 0.50", "x_formula": "largura - 35",
                       "lado": "direito", "aceita_eixo": true}
  }
}
```

#### `constitution_aliases` — Resolução de nomes
```sql
CREATE TABLE constitution_aliases (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nicho      TEXT NOT NULL DEFAULT 'vidros',
    alias      TEXT NOT NULL,       -- ex: 'porta_de_abrir'
    canonical  TEXT NOT NULL,       -- ex: 'porta_pivotante_simples'
    tipo       TEXT NOT NULL,       -- 'tipologia' | 'classificacao_peca'
    origem     TEXT NOT NULL DEFAULT 'seed',
    confianca  REAL NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(nicho, alias, tipo)
);
CREATE INDEX idx_aliases_alias ON constitution_aliases(nicho, alias, tipo);
```

Tipos de alias:
- `tipologia` (93): `'porta_de_abrir'` → `'porta_pivotante_simples'`
- `classificacao_peca` (20): `'folha_fixa'` → `'fixa'`, `'porta'` → `'movel'`

#### `fabricantes` — Fabricantes de ferragens
```sql
CREATE TABLE fabricantes (
    id      TEXT PRIMARY KEY,   -- 'SM', 'HE', 'AL'
    nome    TEXT NOT NULL,
    prefixo TEXT NOT NULL,
    metadata TEXT
);
```

| ID | Nome | Prefixo |
|---|---|---|
| SM | Glasspeças / Santa Marina | SM |
| HE | Fechaduras Hela de Friburgo Ferragens Ltda | HE |
| AL | AL Indústria | AL |

#### `ferragens` — Catálogo de ferragens (158 registros)
```sql
CREATE TABLE ferragens (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo            TEXT NOT NULL,
    codigo_normalizado TEXT NOT NULL,
    fabricante_id     TEXT NOT NULL REFERENCES fabricantes(id),
    nome              TEXT NOT NULL,
    tipo              TEXT,       -- 'dobradica', 'puxador', 'fechadura', ...
    material          TEXT,
    dimensoes_json    TEXT,
    espessura_vidro   TEXT,
    cores_json        TEXT,
    pagina_catalogo   INTEGER,
    confianca         REAL DEFAULT 0.9,
    fonte             TEXT,
    UNIQUE(codigo, fabricante_id)
);
```

#### `kits` — Kits completos (48 registros)
```sql
CREATE TABLE kits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    numero          TEXT NOT NULL,
    fabricante_id   TEXT NOT NULL REFERENCES fabricantes(id),
    nome            TEXT NOT NULL,
    linha           TEXT,
    max_vao_json    TEXT,
    acabamentos_json TEXT,
    pagina_catalogo INTEGER,
    UNIQUE(numero, fabricante_id)
);
```

#### `kit_componentes` — Componentes dos kits (193 registros)
```sql
CREATE TABLE kit_componentes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    kit_id          INTEGER NOT NULL REFERENCES kits(id),
    ferragem_codigo TEXT NOT NULL,
    quantidade      INTEGER DEFAULT 1,
    posicao         TEXT,
    nome            TEXT
);
```

#### `recortes` — Especificações de recortes (124 registros)
```sql
CREATE TABLE recortes (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    ferragem_codigo       TEXT NOT NULL,
    fabricante_id         TEXT NOT NULL REFERENCES fabricantes(id),
    tipo                  TEXT,
    comprimento_mm        REAL,
    largura_mm            REAL,
    furo_diametro_mm      REAL,
    raio_mm               REAL,
    notas                 TEXT,
    pagina_catalogo       INTEGER,
    contexto_aplicacao    TEXT DEFAULT NULL
);
```

#### `equivalencias` — Equivalências cross-fabricante (164 registros)
```sql
CREATE TABLE equivalencias (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_normalizado TEXT NOT NULL,
    fabricante_id      TEXT NOT NULL REFERENCES fabricantes(id),
    codigo_fabricante  TEXT NOT NULL,
    UNIQUE(fabricante_id, codigo_fabricante)
);
```

#### `folgas_nbr` — Tolerâncias NBR (5 registros)
```sql
CREATE TABLE folgas_nbr (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo     TEXT NOT NULL UNIQUE,  -- ex: 'movel_fixo'
    valor_mm REAL NOT NULL,         -- ex: 3.0
    fonte    TEXT
);
```

| Tipo | Valor | Fonte |
|---|---|---|
| `movel_fixo` | 3.0mm | Glasspeças catálogo p.94 |
| `movel_movel` | 4.0mm | Glasspeças catálogo p.94 |
| `movel_piso` | 8.0mm | Glasspeças catálogo p.94 |
| `fixo_fixo` | 1.0mm | Glasspeças catálogo p.94 |
| `movel_alvenaria` | 5.0mm | Glasspeças catálogo p.94 |

#### `formulas` — Fórmulas reutilizáveis (2 registros)
```sql
CREATE TABLE formulas (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                  TEXT NOT NULL,
    formula               TEXT NOT NULL,
    variaveis_json        TEXT,
    ferragens_aplicaveis  TEXT,
    notas                 TEXT,
    fabricante_id         TEXT REFERENCES fabricantes(id)
);
```

### Stats da DB

| Tabela | Registros |
|---|---|
| fabricantes | 3 |
| ferragens | 158 |
| kits | 48 |
| kit_componentes | 193 |
| recortes | 124 |
| equivalencias | 164 |
| formulas | 2 |
| folgas_nbr | 5 |
| constitution_entries | 26 (22 tipologia + 4 preview) |
| constitution_aliases | 114 (93 tipologia + 20 classificacao + 1 outra) |
| constitution_validations | 5 |
| **Total ferragens no catálogo** | **742 registros** |

---

## 6. Data Flow

```
CATÁLOGOS JSON (fonte de verdade dos fabricantes)
  data/catalogs/catalogo_hela.json (57KB)  ──┐
  data/catalogs/catalogo_al_industria.json ──┤──→ tools/catalog_loader.py
  Glasspeças (inline no seed) ───────────────┘         │
                                                        ▼
                                              ┌──────────────────┐
                                              │  Constitution DB  │
                                              │  (SQLite + WAL)   │
                                              │  272KB em disco   │
                                              └────────┬─────────┘
                                                       │
                                                       ▼
POST /api/v1/render → render.py → render_orchestrator.executar()
       │
       ├─ 1. normalizer.normalizar_tipologia(nome)
       │       Camada 1: aliases DB (tipo=tipologia)
       │       Camada 2: fuzzy por tokens
       │       Camada 3: None → Claude Teacher (Modo 2)
       │
       ├─ 2. constitution_engine.resolver_tipologia()
       │       Busca dados + ferragens_por_peca no DB
       │
       ├─ 3. constitution_engine.classificar_peca(peca_nome)
       │       Aliases (tipo=classificacao_peca): 'porta'→'movel', etc.
       │
       ├─ 4. constitution_engine.posicionar_ferragens()
       │       _eval_formula("altura - 50", largura, altura)
       │       eval sandboxado: {"__builtins__": {}}
       │
       ├─ 5. constitution_engine.enriquecer_ferragem_com_catalogo()
       │       Join: blueprint → ferragens + recortes + equivalencias
       │
       ├─ 6. abnt_validator.verificar(pecas, vao)
       │       Compara folgas com folgas_nbr, gera alertas
       │
       └─ 7. svg_template_engine.gerar_svg(resp)
               ↓              ↓              ↓
            SVG            PNG/PDF        Scene JSON
         (response)     (conversion_    (scene_builder)
                         service)            ↓
                                      Three.js HTML
                                      (viewer_3d)

MODOS DE OPERAÇÃO:
  constitution  → tipologia conhecida no DB (caminho feliz)
  claude_teacher→ tipologia desconhecida + ANTHROPIC_API_KEY → Claude infere + registra
  fallback      → sem Anthropic key → módulos _deprecated/
```

---

## 7. Grafo de Dependências

```
main
  → core.constitution          (init_db)
  → core.constitution_seed     (seed)
  → core.limiter               (slowapi)
  → routers.*                  (todos)

routers.render
  → models.render
  → services.render_orchestrator

routers.export
  → models.render
  → core.limiter
  → core.normalizer
  → services.render_orchestrator
  → services.conversion_service (implícito via import)
  → services.preview_generator

routers.viewer_3d
  → models.render
  → core.limiter
  → renderers.scene_builder
  → services.render_orchestrator

routers.chat
  → core.limiter
  → core.normalizer

routers.preview
  → core.constitution
  → core.normalizer
  → services.preview_generator

routers.tipologia_image
  → core.constitution
  → core.normalizer
  → services.image_generator

services.render_orchestrator          ← PONTO CENTRAL
  → core.abnt_validator
  → core.normalizer
  → models.render
  → renderers.svg_template_engine
  → services.constitution_engine
  → [lazy] services.claude_teacher
  → [lazy] app._deprecated.catalogo
  → [lazy] app._deprecated.posicionamento_service
  → [lazy] app._deprecated.kit_resolver

services.constitution_engine
  → core.constitution               (DB queries)
  → core.normalizer
  → models.render

renderers.scene_builder
  → models.render

core.constitution_seed
  → core.constitution               (init_db deve ter rodado antes)

services.claude_teacher
  → core.constitution               (registra resultado)
```

Módulos folha (sem dependências internas): `core.limiter`, `models.feedback`, `services.conversion_service`

---

## 8. Deploy

### Servidor de Produção

```
URL pública   : https://vdx.sw3.tec.br (inferido do CORS config)
Porta local   : 8001 (systemd → uvicorn)
Processo      : systemd unit: vdx-render
User          : sw3innovation (VPS)
Path          : ~/vdx-render-api/
```

### Systemd (inferido do CI/CD)

```ini
[Unit]
Description=VDX Render API

[Service]
WorkingDirectory=/home/sw3innovation/vdx-render-api
ExecStart=/home/sw3innovation/vdx-render-api/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001
Restart=always
```

### CI/CD (`.github/workflows/deploy.yml`)

Trigger: push para `main` com mudanças em `app/**` ou `requirements.txt`

Passos:
1. `py_compile app/main.py` — syntax check rápido
2. `rsync app/` → VPS via SSH (secrets: `VPS_SSH_KEY`, `VPS_PORT`, `VPS_HOST`, `VPS_USER`)
3. `rsync requirements.txt` → VPS
4. SSH: `.venv/bin/pip install -r requirements.txt`
5. SSH: `systemctl restart vdx-render` (via `nsenter` em container alpine)
6. `curl http://localhost:8001/health` — smoke test pós-deploy

### Docker (desenvolvimento / alternativo)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Variáveis de Ambiente

| Variável | Exemplo | Obrigatório | Uso |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Não (degrada para fallback) | Claude Teacher + Chat + Validator |
| `VDX_API_MASTER_KEY` | `vdx-dev-key-local` | Sim | Auth header `X-VDX-Key` |
| `PORT` | `8000` | Não | Porta uvicorn (padrão 8000) |

### CORS Permitidos

```python
allow_origins = [
    "https://vdx.sw3.tec.br",
    "http://localhost:5173",
    "http://localhost:3000",
]
```

---

## 9. Git

### Branches

| Branch | Status | Descrição |
|---|---|---|
| `main` | prod | branch principal |
| `feature/image-generator` | aberta | geração de imagens SD 1.5 |
| `feature/preview-highlight` | aberta | destaque server-side |
| `feature/sync-banco-auto-generate` | aberta | sync automático |
| `fix/add-missing-tipologias` | aberta | tipologias faltando |

### Últimos 20 Commits (main)

```
be49abc feat: auto-geração de preview+imagem em tipologia nova
33becec feat: geração de imagens realistas — Claude (prompt) + SD 1.5 (render)
be8d3e0 feat: adicionar Box de Giro, Sacada 6 Folhas, Janela 4 Folhas ao seed
a19f28f feat: destaque server-side no preview SVG
d2ef844 fix: puxador box na borda direita (largura-40), não centro
2aff4c3 feat: previews mobile — auto-loop animation em touch devices
8b374d0 fix: previews com animação correta + porta 3 folhas
120a26e fix: preview generator não bloqueia event loop + max_tokens 6000
c793a4a feat: previews interativos gerados por Claude Sonnet
dfd4572 feat: validador inteligente + feedback loop
7c49564 fix: registrar chat router + implementar /api/v1/chat
16f57ee feat: Normalizador Inteligente — classificação por tokens + auto-alias
0c63542 feat: Constitution Vidros — knowledge base viva
8bc0e69 polish(svg): desenho técnico para produção
2ac8ce4 fix(svg): labels completos e anti-colisão vertical
39a7a93 refactor: core plugin architecture
f8ffaab fix(posicionamento): dobradiças ESQUERDA, puxador+fechadura DIREITA
0a8f8a3 feat: ABNT completo — 8 aplicações + 3 níveis de alerta
9c3643b feat: motor posicionamento determinístico + puxador com eixo
201996e fix: rename body param to avoid slowapi Request name conflict
```

### .gitignore (principais)

```
.env
__pycache__/
*.pyc
.venv/
data/           ← constitution.db e outputs NÃO versionados
```

> **Nota:** `constitution.db` está no `.gitignore`. Em produção, é criado/populado no startup da aplicação via `init_db()` + `seed()`. Os JSONs dos catálogos (`data/catalogs/*.json`) **estão** versionados.

---

## 10. Dependências

### `requirements.txt` (desenvolvimento completo)

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.0
anthropic==0.34.0
python-dotenv==1.0.1
httpx==0.27.2
slowapi==0.1.9
cairosvg==2.9.0
fpdf2==2.8.7
Pillow==12.1.1
```

### `requirements_prod.txt` (sem conversão)

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.0
anthropic==0.34.0
python-dotenv==1.0.1
httpx==0.27.2
```

### Notas de instalação

- `fpdf2` instala como módulo `fpdf` (não `fpdf2`): `from fpdf import FPDF`
- Em macOS com Python 3.14 (sistema): `pip3 install ... --break-system-packages`
- `slowapi` usa `asyncio.iscoroutinefunction` depreciado no Python 3.16 (warning conhecido, não nosso)
- `cairosvg` requer `libcairo` no sistema (em Debian: `apt install libcairo2`)

---

## 11. Números do Projeto

### Código

| Categoria | Arquivos | Linhas |
|---|---|---|
| Core (constitution, normalizer, abnt, seed) | 5 | 1.580 |
| Routers | 7 | 1.009 |
| Services | 9 | 2.086 |
| Renderers | 2 | 861 |
| Models | 2 | 161 |
| Main | 1 | 53 |
| **Total ativo** | **26** | **5.750** |
| _deprecated | 7 | 3.349 |
| **Total repo** | **33** | **9.099** |

### Testes

| Arquivo | Linhas | Testes | Sprint |
|---|---|---|---|
| `test_constitution_catalog.py` | 541 | ~60 | S1 |
| `test_svg_engine.py` | 393 | ~43 | S2 |
| `test_scene_builder.py` | 303 | 35 | S4 |
| **Total** | **1.237** | **138** | — |

**Status:** 138/138 passando em 0.48s (Python 3.14.3)

### Constitution DB

| Item | Quantidade |
|---|---|
| Tipologias | 22 |
| Aliases de tipologia | 93 |
| Aliases de peça | 20 |
| Fabricantes | 3 |
| Ferragens no catálogo | 158 |
| Kits | 48 |
| Componentes de kit | 193 |
| Recortes | 124 |
| Equivalências | 164 |
| Folgas NBR | 5 |
| Tamanho do DB | 272KB |

### Endpoints

| Categoria | Quantidade |
|---|---|
| Render (SVG) | 1 |
| Export (PNG/PDF/thumb/3D) | 4 |
| Viewer 3D | 1 |
| Tipologias (preview/image/sync) | 6 |
| Chat / Feedback | 2 |
| Infra (health/docs) | 4 |
| **Total** | **18** |

### Cores de vidro suportadas: 6

`incolor`, `verde`, `fume`, `bronze`, `espelho`, `default`

### Materiais PBR de ferragens: 7

`cromado`, `inox`, `preto`, `branco`, `bronze`, `dourado`, `fosco`

### Tipos de animação 3D: 3

`pivotante` (y-axis), `deslizante` (x-translate), `basculante` (x-axis pivot)
