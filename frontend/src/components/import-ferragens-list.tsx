type Ferragem = {
  codigo: string
  fabricante_id: string | null
  nome: string | null
  tipo: string
  posicao_aplicada: { x_mm: number; y_mm: number }
  painel: string
}

type Props = { ferragens: Ferragem[] }

export default function ImportFerragensList({ ferragens }: Props) {
  if (ferragens.length === 0) return null

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      <div className="px-4 py-2.5 border-b border-gray-100 bg-gray-50">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Ferragens ({ferragens.length})
        </span>
      </div>
      <ul className="divide-y divide-gray-100">
        {ferragens.map((f, i) => (
          <li key={i} className="px-4 py-2.5 flex items-start gap-3">
            <span className="mt-0.5 shrink-0 w-6 h-6 rounded-full bg-[#1a5276]/10 text-[#1a5276] text-xs flex items-center justify-center font-semibold">
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-800 truncate">
                {f.nome || f.codigo}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {f.tipo} · painel: {f.painel}
                {f.fabricante_id && ` · ${f.fabricante_id}`}
                {` · x=${f.posicao_aplicada.x_mm}mm y=${f.posicao_aplicada.y_mm}mm`}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
