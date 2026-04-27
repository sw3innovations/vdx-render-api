'use client'

import { useEffect, useState } from 'react'
import type { GrupoPuxador, FabricantePuxador, PuxadorSelecionado } from '@/lib/types'
import PreviewPuxadorSVG from './preview-puxador-svg'

interface SeletorPuxadorProps {
  selected: PuxadorSelecionado | null
  onSelect: (p: PuxadorSelecionado | null) => void
}

export default function SeletorPuxador({ selected, onSelect }: SeletorPuxadorProps) {
  const [grupos, setGrupos] = useState<GrupoPuxador[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)
  const [pickingFabricante, setPickingFabricante] = useState<GrupoPuxador | null>(null)

  useEffect(() => {
    fetch('/api/vdx/v1/catalogo/ferragens?tipo=puxador')
      .then((r) => r.json())
      .then((data: GrupoPuxador[]) => {
        setGrupos(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const handleGrupoClick = (grupo: GrupoPuxador) => {
    if (grupo.fabricantes.length === 1) {
      const fab = grupo.fabricantes[0]
      onSelect({ codigo: fab.codigo, nome: grupo.nome, fabricante_id: fab.id })
      setExpanded(false)
      setPickingFabricante(null)
    } else {
      setPickingFabricante(grupo)
    }
  }

  const handleFabricanteClick = (grupo: GrupoPuxador, fab: FabricantePuxador) => {
    onSelect({ codigo: fab.codigo, nome: grupo.nome, fabricante_id: fab.id })
    setExpanded(false)
    setPickingFabricante(null)
  }

  const handleClear = () => {
    onSelect(null)
    setExpanded(false)
    setPickingFabricante(null)
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-semibold text-gray-700">Puxador</label>
        {selected && (
          <button
            onClick={handleClear}
            className="text-xs text-gray-400 hover:text-red-400 transition-colors"
          >
            remover
          </button>
        )}
      </div>

      {selected ? (
        <button
          onClick={() => { setExpanded(true); setPickingFabricante(null) }}
          className="w-full flex items-center gap-3 p-2.5 rounded-xl border-2 border-[#1a5276] bg-[#1a5276]/5 text-left transition-all"
        >
          <PreviewPuxadorSVG nome={selected.nome} size={40} color="#1a5276" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-800 truncate">{selected.nome}</p>
            <p className="text-xs text-gray-400 font-mono">{selected.codigo} · {selected.fabricante_id}</p>
          </div>
          <span className="text-xs text-[#1a5276] shrink-0">Trocar</span>
        </button>
      ) : (
        <button
          onClick={() => { setExpanded(true); setPickingFabricante(null) }}
          className="w-full py-2 rounded-xl border border-dashed border-gray-300 text-sm text-gray-400 hover:border-[#1a5276]/40 hover:text-[#1a5276]/70 transition-all"
        >
          + Selecionar puxador
        </button>
      )}

      {expanded && (
        <div className="border border-gray-200 rounded-xl bg-white shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              {pickingFabricante ? `Fabricante — ${pickingFabricante.nome}` : 'Escolher modelo'}
            </span>
            <button
              onClick={() => { setExpanded(false); setPickingFabricante(null) }}
              className="text-gray-300 hover:text-gray-500 text-lg leading-none"
            >
              ×
            </button>
          </div>

          <div className="max-h-64 overflow-y-auto">
            {loading && (
              <div className="flex items-center justify-center py-8 text-gray-300 text-sm">
                Carregando…
              </div>
            )}

            {!loading && !pickingFabricante && grupos.map((grupo) => (
              <button
                key={grupo.codigo_normalizado}
                onClick={() => handleGrupoClick(grupo)}
                className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 text-left border-b border-gray-50 last:border-0 transition-colors"
              >
                <PreviewPuxadorSVG nome={grupo.nome} size={40} color="#90B0C8" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-800 truncate">{grupo.nome}</p>
                  <p className="text-xs text-gray-400">
                    {grupo.fabricantes.length > 1
                      ? `${grupo.fabricantes.length} fabricantes`
                      : grupo.fabricantes[0]?.id ?? ''}
                    {' · '}
                    <span className="font-mono">{grupo.codigo_normalizado}</span>
                  </p>
                </div>
                {grupo.fabricantes.length > 1 && (
                  <span className="text-xs text-gray-300 shrink-0">›</span>
                )}
              </button>
            ))}

            {!loading && pickingFabricante && pickingFabricante.fabricantes.map((fab) => (
              <button
                key={fab.id}
                onClick={() => handleFabricanteClick(pickingFabricante, fab)}
                className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 text-left border-b border-gray-50 last:border-0 transition-colors"
              >
                <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center shrink-0">
                  <span className="text-xs font-bold text-gray-500">{fab.id}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-800">{fab.id}</p>
                  <p className="text-xs text-gray-400">
                    {fab.material}
                    {fab.espessura_vidro.length > 0 && ` · ${fab.espessura_vidro.join('/')}mm`}
                    {' · '}
                    <span className="font-mono">{fab.codigo}</span>
                  </p>
                </div>
              </button>
            ))}
          </div>

          {pickingFabricante && (
            <div className="px-3 py-2 border-t border-gray-100">
              <button
                onClick={() => setPickingFabricante(null)}
                className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
              >
                ← Voltar
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
