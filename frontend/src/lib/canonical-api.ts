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
