import type {
  SceneJSON,
  RenderResponse,
  Tipologia,
  PaginatedResponse,
  PecaRequest,
  SmartProjectResponse,
  PhotoToProjectRequest,
  SketchToProjectRequest,
  TextToProjectRequest,
  ProposalRequest,
  ProposalResponse,
  ChatRequest,
  ChatResponse,
  FeedbackRequest,
  FeedbackResponse,
} from './types'

const BASE = '/api/vdx'
const KEY = process.env.NEXT_PUBLIC_VDX_KEY || 'dev-key'

function headers(): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    'X-VDX-Key': KEY,
  }
}

async function apiFetch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${path} falhou (${res.status}): ${text}`)
  }
  return res.json() as Promise<T>
}

async function apiFetchBlob(path: string, body: unknown): Promise<Blob> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${path} falhou (${res.status}): ${text}`)
  }
  return res.blob()
}

/**
 * Auto-generate pecas list from tipologia name + dimensions.
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

  const nome = t.includes('janela') ? 'Folha 1' : 'Porta'
  return [{ nome, largura_mm: largura, altura_mm: altura }]
}

// ─── Render ───────────────────────────────────────────────────────────────────

export async function fetchScene(
  tipologia: string,
  largura: number,
  altura: number,
  corVidro = 'incolor',
  espessura = 8
): Promise<SceneJSON> {
  return apiFetch('/v1/render/export/3d', {
    tipologia_nome: tipologia,
    pecas: autoPecas(tipologia, largura, altura),
    cor_vidro: corVidro,
    espessura_vidro_mm: espessura,
  })
}

export async function fetchRender(
  tipologia: string,
  largura: number,
  altura: number,
  corVidro = 'incolor',
  espessura = 8
): Promise<RenderResponse> {
  return apiFetch('/v1/render', {
    tipologia_nome: tipologia,
    pecas: autoPecas(tipologia, largura, altura),
    cor_vidro: corVidro,
    espessura_vidro_mm: espessura,
  })
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
    throw new Error(`fetchTipologias falhou (${res.status}): ${text}`)
  }
  return res.json() as Promise<PaginatedResponse<Tipologia>>
}

export async function fetchTipologiaPreviewSvg(chave: string): Promise<string> {
  const res = await fetch(`${BASE}/v1/tipologia/${chave}/preview`, {
    headers: { 'X-VDX-Key': KEY },
  })
  if (!res.ok) throw new Error(`fetchTipologiaPreviewSvg falhou (${res.status})`)
  return res.text()
}

export async function exportPng(
  tipologia: string,
  largura: number,
  altura: number,
  corVidro = 'incolor',
  espessura = 8
): Promise<Blob> {
  return apiFetchBlob('/v1/render/export/png', {
    tipologia_nome: tipologia,
    pecas: autoPecas(tipologia, largura, altura),
    cor_vidro: corVidro,
    espessura_vidro_mm: espessura,
  })
}

export async function exportPdf(
  tipologia: string,
  largura: number,
  altura: number,
  corVidro = 'incolor',
  espessura = 8
): Promise<Blob> {
  return apiFetchBlob('/v1/render/export/pdf', {
    tipologia_nome: tipologia,
    pecas: autoPecas(tipologia, largura, altura),
    cor_vidro: corVidro,
    espessura_vidro_mm: espessura,
  })
}

export async function exportThumbnail(
  tipologia: string,
  largura: number,
  altura: number,
  corVidro = 'incolor',
  espessura = 8
): Promise<Blob> {
  return apiFetchBlob('/v1/render/export/thumbnail', {
    tipologia_nome: tipologia,
    pecas: autoPecas(tipologia, largura, altura),
    cor_vidro: corVidro,
    espessura_vidro_mm: espessura,
  })
}

/** Legacy simple proposal export (no empresa/cliente data) */
export async function exportProposal(
  tipologia: string,
  largura: number,
  altura: number,
  corVidro = 'incolor',
  espessura = 8
): Promise<Blob> {
  return apiFetchBlob('/v1/proposal', {
    tipologia_nome: tipologia,
    pecas: autoPecas(tipologia, largura, altura),
    cor_vidro: corVidro,
    espessura_vidro_mm: espessura,
  })
}

/** Full proposal PDF with empresa/cliente data */
export async function generateProposal(req: ProposalRequest): Promise<Blob> {
  return apiFetchBlob('/v1/proposal', req)
}

export async function previewProposal(req: ProposalRequest): Promise<ProposalResponse> {
  return apiFetch('/v1/proposal/preview', req)
}

// ─── 3D Viewer token ──────────────────────────────────────────────────────────

export async function viewerToken(
  tipologia: string,
  largura: number,
  altura: number,
  options: { cor_vidro?: string; espessura?: number; fabricante?: string } = {}
): Promise<{ token: string; url: string; expires_in: number; expires_at: number }> {
  return apiFetch('/v1/3d/viewer/token', {
    tipologia,
    largura,
    altura,
    cor_vidro: options.cor_vidro ?? 'default',
    espessura: options.espessura ?? 8,
    fabricante: options.fabricante ?? null,
  })
}

// ─── Smart Vision ─────────────────────────────────────────────────────────────

export async function photoToProject(req: PhotoToProjectRequest): Promise<SmartProjectResponse> {
  return apiFetch('/v1/smart/photo-to-project', req)
}

export async function sketchToProject(req: SketchToProjectRequest): Promise<SmartProjectResponse> {
  return apiFetch('/v1/smart/sketch-to-project', req)
}

export async function textToProject(req: TextToProjectRequest): Promise<SmartProjectResponse> {
  return apiFetch('/v1/smart/text-to-project', req)
}

// ─── Chat ─────────────────────────────────────────────────────────────────────

export async function chat(req: ChatRequest): Promise<ChatResponse> {
  return apiFetch('/v1/chat', req)
}

// ─── Feedback ─────────────────────────────────────────────────────────────────

export async function feedback(req: FeedbackRequest): Promise<FeedbackResponse> {
  return apiFetch('/v1/feedback', req)
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Download a blob as a file */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

/** Resize an image file to max dimension and return base64 (no data: prefix) */
export async function resizeImageToBase64(file: File, maxDim = 1024): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    const objectUrl = URL.createObjectURL(file)
    img.onload = () => {
      URL.revokeObjectURL(objectUrl)
      const canvas = document.createElement('canvas')
      let { width, height } = img
      if (width > maxDim || height > maxDim) {
        if (width > height) {
          height = Math.round((height * maxDim) / width)
          width = maxDim
        } else {
          width = Math.round((width * maxDim) / height)
          height = maxDim
        }
      }
      canvas.width = width
      canvas.height = height
      canvas.getContext('2d')!.drawImage(img, 0, 0, width, height)
      resolve(canvas.toDataURL('image/jpeg', 0.85).split(',')[1])
    }
    img.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      reject(new Error('Falha ao carregar imagem'))
    }
    img.src = objectUrl
  })
}
