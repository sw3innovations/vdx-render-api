# @vdx/glass-engine

SDK for the **VDX Glass Engine** — photorealistic 3D glass fixture configurator.

## Installation

```bash
npm install @vdx/glass-engine
# peer dependencies
npm install react react-dom three
```

## Quick Start

```tsx
import { VDXClient, VDXViewer, VDXPreview } from '@vdx/glass-engine'

const client = new VDXClient('your-api-key', {
  baseUrl: 'https://api.yourdomain.com', // default: http://localhost:8000
})

// 3D photorealistic viewer
function MyConfigurator() {
  return (
    <VDXViewer
      client={client}
      tipologia="porta_pivotante_simples"
      largura={900}
      altura={2100}
      corVidro="verde"
      style={{ width: '100%', height: 600 }}
      onScreenshot={(blob) => {
        const url = URL.createObjectURL(blob)
        window.open(url)
      }}
    />
  )
}

// Lightweight SVG preview (no Three.js required)
function TipologiaCard({ chave }: { chave: string }) {
  return (
    <VDXPreview
      client={client}
      tipologia={chave}
      width={200}
      height={280}
    />
  )
}
```

## API Client

```ts
const client = new VDXClient('api-key')

// 3D scene JSON (PBR v2.0)
const scene = await client.getScene('porta_pivotante_simples', 900, 2100, 'verde')

// SVG render
const render = await client.getRender('porta_correr_2_folhas', 1200, 2100)

// Export PNG / PDF
const png = await client.exportPng({ tipologia_nome: 'janela_basculante', pecas: [...] })
const pdf = await client.exportPdf({ tipologia_nome: 'janela_basculante', pecas: [...] })

// List tipologias
const { items } = await client.listTipologias(1, 50)

// Proposal PDF
const proposalPdf = await client.generateProposal({
  empresa: { nome: 'Vidraçaria ABC', cnpj: '00.000.000/0001-00' },
  cliente: { nome: 'João Silva', email: 'joao@email.com' },
  itens: [
    {
      descricao: 'Porta Pivotante Simples',
      tipologia: 'porta_pivotante_simples',
      largura_mm: 900,
      altura_mm: 2100,
      quantidade: 2,
      valor_unitario: 1500,
    },
  ],
})

// AI chat assistant
const response = await client.chat({
  messages: [{ role: 'user', content: 'Que tipologia recomenda para um banheiro?' }],
})
console.log(response.reply)

// Health check
const health = await client.health() // { status: 'ok' }
```

## Auto Pecas

The `autoPecas()` helper generates the `pecas` array automatically from the tipologia name:

```ts
import { autoPecas } from '@vdx/glass-engine'

autoPecas('porta_correr_2_folhas', 1200, 2100)
// [{ nome: 'Folha 1', largura_mm: 600, altura_mm: 2100 },
//  { nome: 'Folha 2', largura_mm: 600, altura_mm: 2100 }]

autoPecas('porta_pivotante_dupla_bandeira', 900, 2400)
// [{ nome: 'Bandeira', largura_mm: 900, altura_mm: 384 },
//  { nome: 'Porta',    largura_mm: 900, altura_mm: 2400 }]
```

## Supported tipologias

| Chave | Descrição |
|-------|-----------|
| `porta_pivotante_simples` | Porta pivotante 1 folha |
| `porta_pivotante_dupla_bandeira` | Porta pivotante com bandeira superior |
| `porta_correr_2_folhas` | Porta de correr 2 folhas |
| `porta_correr_3_folhas` | Porta de correr 3 folhas |
| `janela_basculante` | Janela basculante |
| `janela_4_folhas` | Janela 4 folhas |
| `sacada_6_folhas` | Sacada 6 folhas |
| `box_banheiro` | Box de banheiro |
| `box_giro` | Box de giro |
| ... | (use `client.listTipologias()` for full list) |

## Glass colors (`corVidro`)

| Value | Description |
|-------|-------------|
| `incolor` | Clear glass (default) |
| `verde` | Green tinted |
| `fume` | Smoke grey |
| `bronze` | Bronze tinted |
| `espelho` | Mirror |

## TypeScript

All types are exported:

```ts
import type { SceneJSON, VidroScene, FerragemScene, RenderRequest, ProposalRequest } from '@vdx/glass-engine'
```

## Build

```bash
npm run build   # ESM + CJS + .d.ts
npm run dev     # Watch mode
npm run typecheck
```

## License

MIT
