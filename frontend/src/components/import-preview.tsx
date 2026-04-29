'use client'

type Props = {
  svg: string | null
  loading: boolean
}

export default function ImportPreview({ svg, loading }: Props) {
  if (loading) {
    return (
      <div className="w-full aspect-[4/5] max-h-[560px] rounded-2xl bg-gray-100 border border-gray-200 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-gray-400">
          <svg className="animate-spin h-8 w-8" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          <span className="text-sm">Renderizando…</span>
        </div>
      </div>
    )
  }

  if (!svg) {
    return (
      <div className="w-full aspect-[4/5] max-h-[560px] rounded-2xl bg-gray-50 border-2 border-dashed border-gray-200 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-gray-400 px-8 text-center">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-14 h-14 opacity-40">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M9 9h6M9 12h6M9 15h4" />
          </svg>
          <p className="text-sm leading-relaxed">Cole um JSON no painel ao lado<br />e clique em <strong>Gerar Preview</strong></p>
        </div>
      </div>
    )
  }

  return (
    <div
      className="w-full rounded-2xl border border-gray-200 bg-white overflow-hidden shadow-sm flex items-center justify-center p-4"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}
