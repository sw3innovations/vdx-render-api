export type ImportResult = {
  tipologia_chave: string
  svg: string
  png_url: string | null
  pdf_url: string | null
  viewer_3d_url: string | null
  ferragens_resolvidas: Array<{
    codigo: string
    fabricante_id: string | null
    nome: string | null
    tipo: string
    posicao_aplicada: { x_mm: number; y_mm: number }
    painel: string
  }>
  avisos: string[]
}

export type ImportError = {
  tipo: 'validation' | 'business' | 'network' | 'parse'
  mensagem_pt_br: string
  detalhes_tecnicos?: unknown
}

export function isImportError(x: ImportResult | ImportError): x is ImportError {
  return 'tipo' in x && 'mensagem_pt_br' in x
}

export async function importarTipologia(payloadJson: string): Promise<ImportResult | ImportError> {
  if (payloadJson.length > 100_000) {
    return { tipo: 'validation', mensagem_pt_br: 'JSON muito grande (máximo 100 KB).' }
  }

  let payload: unknown
  try {
    payload = JSON.parse(payloadJson)
  } catch (e) {
    return {
      tipo: 'parse',
      mensagem_pt_br: 'JSON inválido. Verifique a sintaxe (faltou vírgula ou aspas?).',
      detalhes_tecnicos: String(e),
    }
  }

  try {
    const res = await fetch('/api/v1/import/tipologia', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (res.status === 422) {
      const detail = await res.json()
      return {
        tipo: 'validation',
        mensagem_pt_br: traduzirErroPydantic(detail),
        detalhes_tecnicos: detail,
      }
    }
    if (res.status === 400) {
      const detail = await res.json()
      return {
        tipo: 'business',
        mensagem_pt_br: detail.detail || 'Erro de validação do conteúdo.',
        detalhes_tecnicos: detail,
      }
    }
    if (!res.ok) {
      return { tipo: 'network', mensagem_pt_br: `Erro do servidor (HTTP ${res.status}).` }
    }

    return (await res.json()) as ImportResult
  } catch (e) {
    return {
      tipo: 'network',
      mensagem_pt_br: 'Erro de rede. Verifique sua conexão e tente novamente.',
      detalhes_tecnicos: String(e),
    }
  }
}

export async function recuperarTipologia(chave: string): Promise<ImportResult | ImportError> {
  try {
    const res = await fetch(`/api/v1/import/${chave}`)
    if (res.status === 404) {
      return { tipo: 'business', mensagem_pt_br: 'Link expirado ou tipologia não encontrada.' }
    }
    if (!res.ok) {
      return { tipo: 'network', mensagem_pt_br: `Erro ao recuperar tipologia (HTTP ${res.status}).` }
    }
    return (await res.json()) as ImportResult
  } catch (e) {
    return {
      tipo: 'network',
      mensagem_pt_br: 'Erro de rede ao recuperar tipologia.',
      detalhes_tecnicos: String(e),
    }
  }
}

function traduzirErroPydantic(detail: { detail?: Array<{ loc: string[]; type: string; msg: string }> }): string {
  if (!Array.isArray(detail.detail)) return 'JSON não corresponde ao formato esperado.'
  const erros = detail.detail.map((e) => {
    const campo = e.loc.slice(1).join('.')
    if (e.type === 'missing') return `Campo "${campo}" obrigatório não foi informado.`
    if (e.type === 'literal_error') return `Campo "${campo}" tem valor inválido.`
    if (e.type.includes('range')) return `Campo "${campo}" está fora do limite permitido.`
    return `Campo "${campo}": ${e.msg}`
  })
  return erros.slice(0, 3).join(' ') + (erros.length > 3 ? ` (+${erros.length - 3} outros erros)` : '')
}

export const EXEMPLO_PAYLOAD = JSON.stringify(
  {
    nome: 'Porta de Abrir Simples',
    categoria: 'porta',
    paineis: [
      {
        nome: 'Folha',
        largura_mm: 900,
        altura_mm: 2100,
        classificacao: 'movel',
        abertura: { modo: 'abrir', lado_dobradica: 'esquerda' },
      },
    ],
    opcoes: { cor: 'incolor', acabamento: 'cromado', incluir_png: true },
  },
  null,
  2
)
