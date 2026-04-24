import type {
  RenderRequest,
  RenderResponse,
  SceneJSON,
  Tipologia,
  PaginatedResponse,
  PecaRequest,
  ProposalRequest,
  ProposalResponse,
  ChatRequest,
  ChatResponse,
  FeedbackRequest,
  FeedbackResponse,
  HealthResponse,
  HealthDetailedResponse,
  SmartProjectResponse,
  PhotoToProjectRequest,
  SketchToProjectRequest,
  TextToProjectRequest,
} from './types'

export interface VDXClientOptions {
  /** Base URL of the VDX API (default: http://localhost:8000) */
  baseUrl?: string
  /** Request timeout in ms (default: 30000) */
  timeout?: number
}

/**
 * Auto-generate pecas list from tipologia name + dimensions.
 * Handles multi-leaf tipologias (6 folhas, 3 folhas, 2 folhas, box, dupla_bandeira).
 */
export function autoPecas(tipologia: string, largura: number, altura: number): PecaRequest[] {
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

  if (t.includes('quatro_folhas') || t.includes('4_folhas') || t.includes('4folhas')) {
    return Array.from({ length: 4 }, (_, i) => ({
      nome: `Folha ${i + 1}`,
      largura_mm: largura / 4,
      altura_mm: altura,
    }))
  }

  const nome = t.includes('janela') ? 'Folha 1' : 'Porta'
  return [{ nome, largura_mm: largura, altura_mm: altura }]
}

/**
 * VDX Glass Engine API client.
 *
 * @example
 * ```ts
 * const client = new VDXClient('my-api-key')
 * const scene = await client.getScene('porta_pivotante_simples', 900, 2100)
 * ```
 */
export class VDXClient {
  private readonly baseUrl: string
  private readonly apiKey: string
  private readonly timeout: number

  constructor(apiKey: string, options: VDXClientOptions = {}) {
    this.apiKey = apiKey
    this.baseUrl = (options.baseUrl ?? 'http://localhost:8000').replace(/\/$/, '')
    this.timeout = options.timeout ?? 30_000
  }

  // ─── Internal ──────────────────────────────────────────────────────────────

  private headers(extra?: Record<string, string>): Record<string, string> {
    return {
      'Content-Type': 'application/json',
      'X-VDX-Key': this.apiKey,
      ...extra,
    }
  }

  private async request<T>(
    method: 'GET' | 'POST',
    path: string,
    body?: unknown,
    binaryResponse = false
  ): Promise<T> {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), this.timeout)

    try {
      const res = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers: method === 'GET'
          ? { 'X-VDX-Key': this.apiKey }
          : this.headers(),
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      })

      if (!res.ok) {
        const text = await res.text().catch(() => res.statusText)
        throw new Error(`VDX API ${method} ${path} failed (${res.status}): ${text}`)
      }

      if (binaryResponse) return res.blob() as unknown as T
      return res.json() as Promise<T>
    } finally {
      clearTimeout(timer)
    }
  }

  // ─── Render ────────────────────────────────────────────────────────────────

  /**
   * Render a tipologia — returns SVG + peca metadata.
   */
  async render(req: RenderRequest): Promise<RenderResponse> {
    return this.request<RenderResponse>('POST', '/api/v1/render', req)
  }

  /**
   * Render and export as PNG blob.
   */
  async exportPng(req: RenderRequest): Promise<Blob> {
    return this.request<Blob>('POST', '/api/v1/render/export/png', req, true)
  }

  /**
   * Render and export as PDF blob.
   */
  async exportPdf(req: RenderRequest): Promise<Blob> {
    return this.request<Blob>('POST', '/api/v1/render/export/pdf', req, true)
  }

  /**
   * Render and export as thumbnail PNG blob.
   */
  async exportThumbnail(req: RenderRequest): Promise<Blob> {
    return this.request<Blob>('POST', '/api/v1/render/export/thumbnail', req, true)
  }

  /**
   * Get full 3D scene JSON (PBR v2.0).
   */
  async export3D(req: RenderRequest): Promise<SceneJSON> {
    return this.request<SceneJSON>('POST', '/api/v1/render/export/3d', req)
  }

  // ─── Convenience wrappers ──────────────────────────────────────────────────

  /**
   * Build the render request from tipologia + dimensions, then fetch 3D scene.
   * `pecas` are auto-generated from the tipologia name.
   */
  async getScene(
    tipologia: string,
    largura: number,
    altura: number,
    corVidro = 'incolor',
    espessura = 8
  ): Promise<SceneJSON> {
    return this.export3D({
      tipologia_nome: tipologia,
      pecas: autoPecas(tipologia, largura, altura),
      cor_vidro: corVidro,
      espessura_vidro_mm: espessura,
    })
  }

  /**
   * Render SVG preview from tipologia + dimensions.
   * `pecas` are auto-generated from the tipologia name.
   */
  async getRender(
    tipologia: string,
    largura: number,
    altura: number,
    corVidro = 'incolor',
    espessura = 8
  ): Promise<RenderResponse> {
    return this.render({
      tipologia_nome: tipologia,
      pecas: autoPecas(tipologia, largura, altura),
      cor_vidro: corVidro,
      espessura_vidro_mm: espessura,
    })
  }

  // ─── 3D Viewer ─────────────────────────────────────────────────────────────

  /**
   * Get the base URL for the server-side 3D viewer HTML page.
   */
  get3DViewerUrl(): string {
    return `${this.baseUrl}/api/v1/3d/viewer`
  }

  /**
   * Create a short-lived shareable URL for the 3D viewer.
   *
   * The URL embeds a signed JWT view token — recipients can open it in a browser,
   * send it via WhatsApp, or embed it in an iframe without the API key being exposed.
   */
  async createShareableUrl(
    tipologia: string,
    largura: number,
    altura: number,
    options: {
      cor_vidro?: string
      espessura?: number
      fabricante?: string
      ttl_seconds?: number
    } = {}
  ): Promise<{ token: string; url: string; expires_in: number; expires_at: number }> {
    return this.request<{ token: string; url: string; expires_in: number; expires_at: number }>(
      'POST',
      '/api/v1/3d/viewer/token',
      {
        tipologia,
        largura,
        altura,
        cor_vidro: options.cor_vidro ?? 'default',
        espessura: options.espessura ?? 8,
        fabricante: options.fabricante ?? null,
        ttl_seconds: options.ttl_seconds ?? undefined,
      }
    )
  }

  // ─── Tipologias ────────────────────────────────────────────────────────────

  /**
   * List all tipologias with preview metadata (paginated).
   */
  async listTipologias(page = 1, perPage = 50): Promise<PaginatedResponse<Tipologia>> {
    return this.request<PaginatedResponse<Tipologia>>(
      'GET',
      `/api/v1/tipologias/previews?page=${page}&per_page=${perPage}`
    )
  }

  /**
   * Get SVG preview for a specific tipologia.
   */
  async getTipologiaPreviewSvg(chave: string): Promise<string> {
    const res = await fetch(`${this.baseUrl}/api/v1/tipologia/${chave}/preview`, {
      headers: { 'X-VDX-Key': this.apiKey },
    })
    if (!res.ok) throw new Error(`getTipologiaPreviewSvg failed (${res.status})`)
    return res.text()
  }

  /**
   * Get PNG preview image for a tipologia.
   */
  async getTipologiaPreviewPng(chave: string): Promise<Blob> {
    const res = await fetch(`${this.baseUrl}/api/v1/tipologia/${chave}/preview/png`, {
      headers: { 'X-VDX-Key': this.apiKey },
    })
    if (!res.ok) throw new Error(`getTipologiaPreviewPng failed (${res.status})`)
    return res.blob()
  }

  /**
   * Get AI-generated thumbnail image for a tipologia.
   */
  async getTipologiaThumbnail(chave: string): Promise<Blob> {
    const res = await fetch(`${this.baseUrl}/api/v1/tipologia/${chave}/preview/thumbnail`, {
      headers: { 'X-VDX-Key': this.apiKey },
    })
    if (!res.ok) throw new Error(`getTipologiaThumbnail failed (${res.status})`)
    return res.blob()
  }

  /**
   * Get AI-generated realistic image for a tipologia.
   */
  async getTipologiaImage(chave: string): Promise<Blob> {
    const res = await fetch(`${this.baseUrl}/api/v1/tipologia/${chave}/image`, {
      headers: { 'X-VDX-Key': this.apiKey },
    })
    if (!res.ok) throw new Error(`getTipologiaImage failed (${res.status})`)
    return res.blob()
  }

  /**
   * Sync tipologias from the database seed.
   */
  async syncTipologias(): Promise<unknown> {
    return this.request<unknown>('POST', '/api/v1/tipologia/sync')
  }

  /**
   * Regenerate all tipologia previews.
   */
  async regeneratePreviews(): Promise<unknown> {
    return this.request<unknown>('POST', '/api/v1/tipologias/previews/regenerar')
  }

  /**
   * Generate all tipologia AI images.
   */
  async generateAllImages(): Promise<unknown> {
    return this.request<unknown>('POST', '/api/v1/tipologias/images/gerar-todas')
  }

  // ─── Smart Vision ──────────────────────────────────────────────────────────

  /**
   * Analyze a real photo of a vão and generate a complete project.
   */
  async photoToProject(req: PhotoToProjectRequest): Promise<SmartProjectResponse> {
    return this.request<SmartProjectResponse>('POST', '/api/v1/smart/photo-to-project', req)
  }

  /**
   * Analyze a hand-drawn sketch and generate a complete project.
   */
  async sketchToProject(req: SketchToProjectRequest): Promise<SmartProjectResponse> {
    return this.request<SmartProjectResponse>('POST', '/api/v1/smart/sketch-to-project', req)
  }

  /**
   * Interpret a text description and generate a complete project (no image needed).
   */
  async textToProject(req: TextToProjectRequest): Promise<SmartProjectResponse> {
    return this.request<SmartProjectResponse>('POST', '/api/v1/smart/text-to-project', req)
  }

  // ─── Proposal ──────────────────────────────────────────────────────────────

  /**
   * Generate a commercial proposal PDF.
   */
  async generateProposal(req: ProposalRequest): Promise<Blob> {
    return this.request<Blob>('POST', '/api/v1/proposal', req, true)
  }

  /**
   * Preview proposal metadata (without generating PDF).
   */
  async previewProposal(req: ProposalRequest): Promise<ProposalResponse> {
    return this.request<ProposalResponse>('POST', '/api/v1/proposal/preview', req)
  }

  // ─── Chat ──────────────────────────────────────────────────────────────────

  /**
   * Send a message to the VDX AI assistant.
   */
  async chat(req: ChatRequest): Promise<ChatResponse> {
    return this.request<ChatResponse>('POST', '/api/v1/chat', req)
  }

  // ─── Feedback ──────────────────────────────────────────────────────────────

  /**
   * Submit user feedback for a render.
   */
  async submitFeedback(req: FeedbackRequest): Promise<FeedbackResponse> {
    return this.request<FeedbackResponse>('POST', '/api/v1/feedback', req)
  }

  // ─── Health ────────────────────────────────────────────────────────────────

  /**
   * Check API health (unauthenticated).
   */
  async health(): Promise<HealthResponse> {
    const res = await fetch(`${this.baseUrl}/health`)
    if (!res.ok) throw new Error(`health check failed (${res.status})`)
    return res.json() as Promise<HealthResponse>
  }

  /**
   * Detailed health check including DB, cache, uptime.
   */
  async healthDetailed(): Promise<HealthDetailedResponse> {
    const res = await fetch(`${this.baseUrl}/health/detailed`)
    if (!res.ok) throw new Error(`healthDetailed failed (${res.status})`)
    return res.json() as Promise<HealthDetailedResponse>
  }
}
