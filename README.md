# VDX Render API

Motor de desenho técnico SVG para aplicações de vidro temperado.

## Uso rápido

```bash
POST /api/v1/render
Header: X-VDX-Key: sua-chave
Content-Type: application/json

{
  "tipologia_nome": "Box Frontal 2 Folhas",
  "pecas": [
    {"nome": "FIXO", "largura_mm": 600, "altura_mm": 1200,
     "ferragens": [{"tipo": "bate_fecha", "nome": "Bate Fecha Mini"}]},
    {"nome": "PORTA", "largura_mm": 650, "altura_mm": 1200,
     "ferragens": [{"tipo": "puxador", "nome": "Puxador Arco"}]}
  ],
  "opcoes": {"tema": "tecnico", "mostrar_cotas": true}
}
```

## Formatos suportados

- **SVG** (fase 1) — retornado inline no JSON
- PNG, PDF (fase 2)

## Layouts

| Layout | Quando |
|---|---|
| `paralelas` | folhas lado a lado (box, janelas, portas correr) |
| `bandeira_topo` | bandeira superior + portas abaixo |
| `canto_l` | box canto, guarda-corpo canto |
| `fixo_movel_fixo` | porta correr com fixos laterais |
| `basculante` | janelas basculante, maxim-ar |
| `cobertura` | coberturas e claraboias |
| `paineis_lineares` | guarda-corpo, sacadas, fachadas |

## Temas

- `tecnico` — azul VDX (`#185FA5`) com fill `#EEF3FB`
- `clean` — preto e branco

## Variáveis de ambiente

```
ANTHROPIC_API_KEY=sk-ant-...   # opcional — ativa inferência de ferragens via Claude
VDX_API_MASTER_KEY=...         # qualquer valor não-vazio
PORT=8000
```

## Rodar localmente

```bash
pip install -r requirements.txt
cp .env.example .env
# edite .env com sua ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

Docs interativas: http://localhost:8000/docs
