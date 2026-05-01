export interface CanonicalFerragem {
  id: number
  canonical_id: string          // código base canônico (ex: "1101", "01.24.026")
  codigo_normalizado: string
  tipo: string | null
  subtipo: string | null
  nome_apresentacao: string
  fabricante_codigo: string | null
  fabricante_nome: string | null
  comprimento_mm: number | null
  diametro_mm: number | null
  material_nome: string | null
  acabamento_nome: string | null
}

export interface CanonicalFerragemAgrupada {
  canonical_id: string
  tipo: string | null
  subtipo: string | null
  nome_apresentacao: string
  variantes: CanonicalFerragem[]
  total_variantes: number
}

export interface FerragensResponse {
  total: number
  ferragens: CanonicalFerragem[]
}

export interface FiltrosFerragem {
  fabricantes: { id: string; nome: string }[]
  subtipos: string[]
  comprimento_min: number | null
  comprimento_max: number | null
}

interface FerragensParams {
  subtipo?: string
  fabricante?: string
  busca?: string
  comp_min?: number
  comp_max?: number
  limit?: number
}

export async function listarFerragens(tipo: string, params?: FerragensParams): Promise<FerragensResponse> {
  const qs = new URLSearchParams({ tipo, limit: String(params?.limit ?? 100) })
  if (params?.subtipo) qs.set('subtipo', params.subtipo)
  if (params?.fabricante) qs.set('fabricante', params.fabricante)
  if (params?.busca) qs.set('busca', params.busca)
  if (params?.comp_min != null) qs.set('comp_min', String(params.comp_min))
  if (params?.comp_max != null) qs.set('comp_max', String(params.comp_max))
  const res = await fetch(`/api/v1/canonical/ferragens?${qs}`)
  if (!res.ok) throw new Error(`listarFerragens falhou (${res.status})`)
  return res.json() as Promise<FerragensResponse>
}

export async function listarPuxadores(params?: FerragensParams): Promise<FerragensResponse> {
  return listarFerragens('puxador', params)
}

export async function buscarVariantesFerragem(canonicalId: string): Promise<CanonicalFerragemAgrupada> {
  const res = await fetch(`/api/v1/canonical/ferragens/${encodeURIComponent(canonicalId)}/variantes`)
  if (!res.ok) throw new Error(`buscarVariantesFerragem falhou (${res.status})`)
  return res.json() as Promise<CanonicalFerragemAgrupada>
}

export async function listarFiltrosFerragem(tipo = 'puxador'): Promise<FiltrosFerragem> {
  const res = await fetch(`/api/v1/canonical/ferragens/filtros?tipo=${tipo}`)
  if (!res.ok) throw new Error(`listarFiltrosFerragem falhou (${res.status})`)
  return res.json() as Promise<FiltrosFerragem>
}

// ─── v2 Ferragens ────────────────────────────────────────────────────────────

export interface CanonicalV2 {
  canonical_id: string
  linha: string | null
  categoria: string | null
  subcategoria: string | null
  nome_apresentacao: string
  recorte_largura_mm: number | null
  recorte_altura_mm: number | null
  confidence: string | null
  fontes_pdf: string | null
  obs: string | null
}

export interface FiltrosV2 {
  total_canonicals: number
  linhas: string[]
  categorias: string[]
}

export interface CanonicalsV2Response {
  total: number
  canonicals: CanonicalV2[]
}

export async function listarCanonicalsV2(params?: {
  linha?: string
  categoria?: string
  busca?: string
}): Promise<CanonicalsV2Response> {
  const qs = new URLSearchParams({ limit: '500' })
  if (params?.linha) qs.set('linha', params.linha)
  if (params?.categoria) qs.set('categoria', params.categoria)
  if (params?.busca) qs.set('busca', params.busca)
  const res = await fetch(`/api/v2/ferragens/?${qs}`)
  if (!res.ok) throw new Error(`listarCanonicalsV2 falhou (${res.status})`)
  return res.json() as Promise<CanonicalsV2Response>
}

export async function listarFiltrosV2(): Promise<FiltrosV2> {
  const res = await fetch('/api/v2/ferragens/filtros')
  if (!res.ok) throw new Error(`listarFiltrosV2 falhou (${res.status})`)
  return res.json() as Promise<FiltrosV2>
}

// ─── Tipologias ───────────────────────────────────────────────────────────────

export interface TipologiaCanonica {
  id: number
  codigo: string
  nome_apresentacao: string
  categoria: string | null
  fonte_origem: string
  tem_renderer: boolean
  nu_tip_dump?: number | null
  schema_render?: string | null
}

export interface TipologiasResponse {
  total: number
  tipologias: TipologiaCanonica[]
}

export async function fetchCanonicalTipologias(limit = 200): Promise<TipologiasResponse> {
  const res = await fetch(`/api/v1/canonical/tipologias?limit=${limit}`)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`fetchCanonicalTipologias falhou (${res.status}): ${text}`)
  }
  return res.json() as Promise<TipologiasResponse>
}
