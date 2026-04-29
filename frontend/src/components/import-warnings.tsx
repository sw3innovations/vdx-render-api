type Props = { avisos: string[] }

export default function ImportWarnings({ avisos }: Props) {
  if (avisos.length === 0) return null

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 flex gap-3">
      <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-amber-500 shrink-0 mt-0.5">
        <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
      </svg>
      <div>
        <p className="text-sm font-semibold text-amber-800 mb-1">Avisos</p>
        <ul className="space-y-0.5">
          {avisos.map((a, i) => (
            <li key={i} className="text-sm text-amber-700">{a}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}
