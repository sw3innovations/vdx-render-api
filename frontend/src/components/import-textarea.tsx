'use client'

import { EXEMPLO_PAYLOAD } from '@/lib/import-api'

type Props = {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  loading: boolean
}

export default function ImportTextarea({ value, onChange, onSubmit, loading }: Props) {
  const bytes = new TextEncoder().encode(value).length
  const tooBig = bytes > 100_000

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-semibold text-gray-700">Payload JSON (contrato v2)</label>
        <span className={`text-xs font-mono ${tooBig ? 'text-red-500' : 'text-gray-400'}`}>
          {(bytes / 1024).toFixed(1)} KB / 100 KB
        </span>
      </div>

      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={22}
        spellCheck={false}
        className="w-full font-mono text-xs bg-gray-950 text-green-300 rounded-xl px-4 py-3 resize-none focus:outline-none focus:ring-2 focus:ring-[#1a5276]/50 border border-gray-800"
        placeholder={'{\n  "nome": "Minha Tipologia",\n  "paineis": [...]\n}'}
      />

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onChange(EXEMPLO_PAYLOAD)}
          className="flex-1 text-sm px-3 py-2 rounded-lg border border-[#1a5276]/40 text-[#1a5276] hover:bg-[#1a5276]/5 transition-colors"
        >
          Colar exemplo
        </button>
        <button
          type="button"
          onClick={() => onChange('')}
          disabled={!value}
          className="text-sm px-3 py-2 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors disabled:opacity-40"
        >
          Limpar
        </button>
      </div>

      <button
        type="button"
        onClick={onSubmit}
        disabled={!value.trim() || tooBig || loading}
        className="w-full py-2.5 rounded-xl bg-[#1a5276] text-white text-sm font-semibold hover:bg-[#154360] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Gerando…
          </>
        ) : (
          'Gerar Preview'
        )}
      </button>
    </div>
  )
}
