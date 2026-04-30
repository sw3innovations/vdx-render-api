'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { PuxadorSelecionado } from '@/lib/types'
import type { CanonicalFerragem, FiltrosFerragem } from '@/lib/canonical-api'
import { listarPuxadores, listarFiltrosFerragem } from '@/lib/canonical-api'
import { cn } from '@/lib/utils'
import PreviewPuxadorSVG from './preview-puxador-svg'

interface SeletorPuxadorProps {
  selected: PuxadorSelecionado | null
  onSelect: (p: PuxadorSelecionado | null) => void
}

function toSelecionado(f: CanonicalFerragem): PuxadorSelecionado {
  return {
    codigo: f.codigo_normalizado,
    nome: f.nome_apresentacao,
    fabricante_id: f.fabricante_codigo ?? '',
  }
}

// ── Filtros state ─────────────────────────────────────────────────────────────

interface Filtros {
  fabricante: string
  subtipo: string
  busca: string
  comp_min: string
  comp_max: string
}

const FILTROS_VAZIOS: Filtros = { fabricante: '', subtipo: '', busca: '', comp_min: '', comp_max: '' }

// ── Sub-components ────────────────────────────────────────────────────────────

function PuxadorCard({
  ferragem,
  onSelect,
}: {
  ferragem: CanonicalFerragem
  onSelect: (f: CanonicalFerragem) => void
}) {
  return (
    <button
      onClick={() => onSelect(ferragem)}
      className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 text-left border-b border-gray-50 last:border-0 transition-colors"
    >
      <PreviewPuxadorSVG nome={ferragem.nome_apresentacao} size={40} color="#90B0C8" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800 truncate">{ferragem.nome_apresentacao}</p>
        <p className="text-xs text-gray-400 truncate">
          {ferragem.fabricante_nome ?? ferragem.fabricante_codigo ?? '—'}
          {ferragem.comprimento_mm != null && ` · ${ferragem.comprimento_mm}mm`}
          {' · '}
          <span className="font-mono">{ferragem.codigo_normalizado}</span>
        </p>
      </div>
    </button>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function SeletorPuxador({ selected, onSelect }: SeletorPuxadorProps) {
  const [open, setOpen] = useState(false)
  const [filtros, setFiltros] = useState<Filtros>(FILTROS_VAZIOS)
  const [ferragens, setFerragens] = useState<CanonicalFerragem[]>([])
  const [filtrosData, setFiltrosData] = useState<FiltrosFerragem | null>(null)
  const [loading, setLoading] = useState(false)
  const buscarTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Load filtros metadata once when modal opens
  useEffect(() => {
    if (!open || filtrosData) return
    listarFiltrosFerragem('puxador')
      .then(setFiltrosData)
      .catch(() => {})
  }, [open, filtrosData])

  const fetchFerragens = useCallback((f: Filtros) => {
    setLoading(true)
    listarPuxadores({
      fabricante: f.fabricante || undefined,
      subtipo: f.subtipo || undefined,
      busca: f.busca || undefined,
      comp_min: f.comp_min ? Number(f.comp_min) : undefined,
      comp_max: f.comp_max ? Number(f.comp_max) : undefined,
    })
      .then((res) => setFerragens(res.ferragens))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  // Fetch ferragens when modal opens or filters change
  useEffect(() => {
    if (!open) return
    if (buscarTimeout.current) clearTimeout(buscarTimeout.current)
    buscarTimeout.current = setTimeout(() => fetchFerragens(filtros), 250)
    return () => {
      if (buscarTimeout.current) clearTimeout(buscarTimeout.current)
    }
  }, [open, filtros, fetchFerragens])

  const handleSelect = (f: CanonicalFerragem) => {
    onSelect(toSelecionado(f))
    setOpen(false)
  }

  const handleClear = () => {
    onSelect(null)
    setOpen(false)
  }

  const setFiltro = (key: keyof Filtros, value: string) =>
    setFiltros((prev) => ({ ...prev, [key]: value }))

  return (
    <div className="space-y-2">
      {/* Label row */}
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

      {/* Trigger */}
      {selected ? (
        <button
          onClick={() => setOpen(true)}
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
          onClick={() => setOpen(true)}
          className="w-full py-2 rounded-xl border border-dashed border-gray-300 text-sm text-gray-400 hover:border-[#1a5276]/40 hover:text-[#1a5276]/70 transition-all"
        >
          + Selecionar puxador
        </button>
      )}

      {/* Modal overlay */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40"
          onClick={(e) => { if (e.target === e.currentTarget) setOpen(false) }}
        >
          <div className="w-full sm:max-w-lg bg-white rounded-t-2xl sm:rounded-2xl shadow-xl flex flex-col max-h-[90vh] sm:max-h-[80vh]">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 shrink-0">
              <span className="text-sm font-semibold text-gray-700">Escolher puxador</span>
              <button
                onClick={() => setOpen(false)}
                className="text-gray-300 hover:text-gray-500 text-xl leading-none"
              >
                ×
              </button>
            </div>

            {/* Search + filters */}
            <div className="px-4 py-3 space-y-2 border-b border-gray-100 shrink-0">
              {/* Text search */}
              <input
                type="text"
                placeholder="Buscar por nome…"
                value={filtros.busca}
                onChange={(e) => setFiltro('busca', e.target.value)}
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-[#1a5276]/50"
              />

              {/* Filter row */}
              <div className="flex gap-2 flex-wrap">
                {/* Fabricante */}
                {filtrosData && filtrosData.fabricantes.length > 0 && (
                  <select
                    value={filtros.fabricante}
                    onChange={(e) => setFiltro('fabricante', e.target.value)}
                    className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:border-[#1a5276]/50 bg-white text-gray-600"
                  >
                    <option value="">Todos fabricantes</option>
                    {filtrosData.fabricantes.map((f) => (
                      <option key={f.id} value={f.id}>{f.nome}</option>
                    ))}
                  </select>
                )}

                {/* Subtipo */}
                {filtrosData && filtrosData.subtipos.length > 0 && (
                  <select
                    value={filtros.subtipo}
                    onChange={(e) => setFiltro('subtipo', e.target.value)}
                    className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:border-[#1a5276]/50 bg-white text-gray-600"
                  >
                    <option value="">Todos formatos</option>
                    {filtrosData.subtipos.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                )}

                {/* Comprimento range */}
                {filtrosData && filtrosData.comprimento_max != null && (
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      placeholder={String(filtrosData.comprimento_min ?? 0)}
                      value={filtros.comp_min}
                      onChange={(e) => setFiltro('comp_min', e.target.value)}
                      className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 w-20 focus:outline-none focus:border-[#1a5276]/50"
                    />
                    <span className="text-xs text-gray-400">–</span>
                    <input
                      type="number"
                      placeholder={String(filtrosData.comprimento_max)}
                      value={filtros.comp_max}
                      onChange={(e) => setFiltro('comp_max', e.target.value)}
                      className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 w-20 focus:outline-none focus:border-[#1a5276]/50"
                    />
                    <span className="text-xs text-gray-400">mm</span>
                  </div>
                )}

                {/* Reset filters */}
                {(filtros.fabricante || filtros.subtipo || filtros.busca || filtros.comp_min || filtros.comp_max) && (
                  <button
                    onClick={() => setFiltros(FILTROS_VAZIOS)}
                    className="text-xs text-gray-400 hover:text-gray-600 transition-colors px-2 py-1.5"
                  >
                    limpar
                  </button>
                )}
              </div>
            </div>

            {/* List */}
            <div className="overflow-y-auto flex-1">
              {loading && (
                <div className="flex items-center justify-center py-10 text-gray-300 text-sm">
                  Carregando…
                </div>
              )}
              {!loading && ferragens.length === 0 && (
                <div className="flex items-center justify-center py-10 text-gray-400 text-sm">
                  Nenhum puxador encontrado
                </div>
              )}
              {!loading && ferragens.map((f) => (
                <PuxadorCard key={f.id} ferragem={f} onSelect={handleSelect} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
