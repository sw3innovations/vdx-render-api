export interface CanonicalFerragem {
  id: number
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

export async function listarPuxadores(params?: {
  subtipo?: string
  fabricante?: string
  busca?: string
  comp_min?: number
  comp_max?: number
  limit?: number
}): Promise<FerragensResponse> {
  const qs = new URLSearchParams({ tipo: 'puxador', limit: String(params?.limit ?? 100) })
  if (params?.subtipo) qs.set('subtipo', params.subtipo)
  if (params?.fabricante) qs.set('fabricante', params.fabricante)
  if (params?.busca) qs.set('busca', params.busca)
  if (params?.comp_min != null) qs.set('comp_min', String(params.comp_min))
  if (params?.comp_max != null) qs.set('comp_max', String(params.comp_max))
  const res = await fetch(`/api/v1/canonical/ferragens?${qs}`)
  if (!res.ok) throw new Error(`listarPuxadores falhou (${res.status})`)
  return res.json() as Promise<FerragensResponse>
}

export async function listarFiltrosFerragem(tipo = 'puxador'): Promise<FiltrosFerragem> {
  const res = await fetch(`/api/v1/canonical/ferragens/filtros?tipo=${tipo}`)
  if (!res.ok) throw new Error(`listarFiltrosFerragem falhou (${res.status})`)
  return res.json() as Promise<FiltrosFerragem>
}

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
