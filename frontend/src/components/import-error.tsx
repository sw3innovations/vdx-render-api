'use client'

import { useState } from 'react'
import type { ImportError } from '@/lib/import-api'

type Props = { error: ImportError }

export default function ImportErrorDisplay({ error }: Props) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 flex gap-3">
      <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-red-500 shrink-0 mt-0.5">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
      </svg>
      <div className="flex-1">
        <p className="text-sm font-semibold text-red-800">{error.mensagem_pt_br}</p>
        {error.detalhes_tecnicos != null && (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="mt-1.5 text-xs text-red-600 hover:underline"
          >
            {expanded ? 'Ocultar detalhes técnicos' : 'Ver detalhes técnicos'}
          </button>
        )}
        {expanded && error.detalhes_tecnicos != null && (
          <pre className="mt-2 text-xs text-red-700 bg-red-100 rounded-lg p-3 overflow-auto max-h-40 whitespace-pre-wrap">
            {typeof error.detalhes_tecnicos === 'string'
              ? error.detalhes_tecnicos
              : JSON.stringify(error.detalhes_tecnicos, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}
