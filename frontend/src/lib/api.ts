import type {
  SceneJSON,
  RenderResponse,
  Tipologia,
  PaginatedResponse,
  PecaRequest,
} from './types'

const BASE = '/api/vdx'
const KEY = process.env.NEXT_PUBLIC_VDX_KEY || 'dev-key'

function headers(): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    'X-VDX-Key': KEY,
  }
}

/**
 * Auto-generate pecas list from tipologia name + dimensions.
 * Handles multi-leaf tipologias (6 folhas, 3 folhas, 2 folhas, box, etc.)
 */
function autoPecas(tipologia: string, largura: number, altura: number): PecaRequest[] {
  const t = tipologia.toLowerCase()

  if (t.includes('6_folhas') || t.includes('6folhas')) {
    return Array.from({ length: 6 }, (_, i) => ({
      nome: `Folha ${i + 1}`,
      largura_mm: largura / 6,
      altura_mm: altura,
    }))
  }

  if (t.includes('3_folhas') || t.includes('3folhas')) {
    return Array.from({ length: 3 }, (_, i) => ({
      nome: `Folha ${i + 1}`,
      largura_mm: largura / 3,
      altura_mm: altura,
    }))
  }

  if (t.includes('2_folhas') || t.includes('2folhas') || t.includes('box')) {
    return [
      { nome: 'Folha 1', largura_mm: largura / 2, altura_mm: altura },
      { nome: 'Folha 2', largura_mm: largura / 2, altura_mm: altura },
    ]
  }

  if (t.includes('dupla_bandeira')) {
    return [
      { nome: 'Bandeira', largura_mm: largura, altura_mm: Math.min(400, altura * 0.16) },
      { nome: 'Porta', largura_mm: largura, altura_mm: altura },
    ]
  }

  // Default: single leaf named "Porta" or "Folha 1"
  const nome = t.includes('janela') ? 'Folha 1' : 'Porta'
  return [{ nome, largura_mm: largura, altura_mm: altura }]
}

// ─── API calls ────────────────────────────────────────────────────────────────

export async function fetchScene(
  tipologia: string,
  largura: number,
  altura: number,
  corVidro = 'incolor',
  espessura = 8
): Promise<SceneJSON> {
  const pecas = autoPecas(tipologia, largura, altura)
  const res = await fetch(`${BASE}/v1/render/export/3d`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      tipologia_nome: tipologia,
      pecas,
      cor_vidro: corVidro,
      espessura_vidro_mm: espessura,
    }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`fetchScene failed (${res.status}): ${text}`)
  }
  return res.json() as Promise<SceneJSON>
}

export async function fetchRender(
  tipologia: string,
  largura: number,
  altura: number,
  corVidro = 'incolor',
  espessura = 8
): Promise<RenderResponse> {
  const pecas = autoPecas(tipologia, largura, altura)
  const res = await fetch(`${BASE}/v1/render`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      tipologia_nome: tipologia,
      pecas,
      cor_vidro: corVidro,
      espessura_vidro_mm: espessura,
    }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`fetchRender failed (${res.status}): ${text}`)
  }
  return res.json() as Promise<RenderResponse>
}

export async function fetchTipologias(
  page = 1,
  perPage = 50
): Promise<PaginatedResponse<Tipologia>> {
  const res = await fetch(`${BASE}/v1/tipologias/previews?page=${page}&per_page=${perPage}`, {
    headers: { 'X-VDX-Key': KEY },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`fetchTipologias failed (${res.status}): ${text}`)
  }
  return res.json() as Promise<PaginatedResponse<Tipologia>>
}

export async function fetchTipologiaPreviewSvg(chave: string): Promise<string> {
  const res = await fetch(`${BASE}/v1/tipologia/${chave}/preview`, {
    headers: { 'X-VDX-Key': KEY },
  })
  if (!res.ok) throw new Error(`fetchTipologiaPreviewSvg failed (${res.status})`)
  return res.text()
}

export async function exportPng(
  tipologia: string,
  largura: number,
  altura: number,
  corVidro = 'incolor',
  espessura = 8
): Promise<Blob> {
  const pecas = autoPecas(tipologia, largura, altura)
  const res = await fetch(`${BASE}/v1/render/export/png`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      tipologia_nome: tipologia,
      pecas,
      cor_vidro: corVidro,
      espessura_vidro_mm: espessura,
    }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`exportPng failed (${res.status}): ${text}`)
  }
  return res.blob()
}

export async function exportPdf(
  tipologia: string,
  largura: number,
  altura: number,
  corVidro = 'incolor',
  espessura = 8
): Promise<Blob> {
  const pecas = autoPecas(tipologia, largura, altura)
  const res = await fetch(`${BASE}/v1/render/export/pdf`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      tipologia_nome: tipologia,
      pecas,
      cor_vidro: corVidro,
      espessura_vidro_mm: espessura,
    }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`exportPdf failed (${res.status}): ${text}`)
  }
  return res.blob()
}

export async function exportProposal(
  tipologia: string,
  largura: number,
  altura: number,
  corVidro = 'incolor',
  espessura = 8
): Promise<Blob> {
  const pecas = autoPecas(tipologia, largura, altura)
  const res = await fetch(`${BASE}/v1/proposal`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      tipologia_nome: tipologia,
      pecas,
      cor_vidro: corVidro,
      espessura_vidro_mm: espessura,
    }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`exportProposal failed (${res.status}): ${text}`)
  }
  return res.blob()
}

/** Helper: download a blob as a file */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
