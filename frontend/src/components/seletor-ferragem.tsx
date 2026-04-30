'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { FerragemSelecionada } from '@/lib/types'
import type { CanonicalFerragem, FiltrosFerragem } from '@/lib/canonical-api'
import { listarFerragens, listarFiltrosFerragem } from '@/lib/canonical-api'

function toSelecionada(f: CanonicalFerragem): FerragemSelecionada {
  return {
    codigo: f.codigo_normalizado,
    nome: f.nome_apresentacao,
    fabricante_id: f.fabricante_codigo ?? '',
  }
}

interface Filtros {
  fabricante: string
  subtipo: string
  busca: string
  comp_min: string
  comp_max: string
}

const FILTROS_VAZIOS: Filtros = { fabricante: '', subtipo: '', busca: '', comp_min: '', comp_max: '' }

function HardwareIcon({ size = 40 }: { size?: number }) {
  return (
    <div
      className="rounded-lg bg-gray-100 flex items-center justify-center shrink-0"
      style={{ width: size, height: size }}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        style={{ width: size * 0.5, height: size * 0.5 }}
        className="text-gray-400"
      >
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12" />
      </svg>
    </div>
  )
}

export interface SeletorFerragemProps {
  tipo: string
  label: string
  selected: FerragemSelecionada | null
  onSelect: (f: FerragemSelecionada | null) => void
}

export default function SeletorFerragem({ tipo, label, selected, onSelect }: SeletorFerragemProps) {
  const [open, setOpen] = useState(false)
  const [filtros, setFiltros] = useState<Filtros>(FILTROS_VAZIOS)
  const [ferragens, setFerragens] = useState<CanonicalFerragem[]>([])
  const [filtrosData, setFiltrosData] = useState<FiltrosFerragem | null>(null)
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!open || filtrosData) return
    listarFiltrosFerragem(tipo).then(setFiltrosData).catch(() => {})
  }, [open, filtrosData, tipo])

  const fetchFerragens = useCallback(
    (f: Filtros) => {
      setLoading(true)
      listarFerragens(tipo, {
        fabricante: f.fabricante || undefined,
        subtipo: f.subtipo || undefined,
        busca: f.busca || undefined,
        comp_min: f.comp_min ? Number(f.comp_min) : undefined,
        comp_max: f.comp_max ? Number(f.comp_max) : undefined,
      })
        .then((res) => setFerragens(res.ferragens))
        .catch(() => {})
        .finally(() => setLoading(false))
    },
    [tipo]
  )

  useEffect(() => {
    if (!open) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => fetchFerragens(filtros), 250)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [open, filtros, fetchFerragens])

  const handleSelect = (f: CanonicalFerragem) => {
    onSelect(toSelecionada(f))
    setOpen(false)
  }

  const setFiltro = (key: keyof Filtros, value: string) =>
    setFiltros((prev) => ({ ...prev, [key]: value }))

  const labelLower = label.toLowerCase()

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-semibold text-gray-700">{label}</label>
        {selected && (
          <button
            onClick={() => { onSelect(null); setOpen(false) }}
            className="text-xs text-gray-400 hover:text-red-400 transition-colors"
          >
            remover
          </button>
        )}
      </div>

      {selected ? (
        <button
          onClick={() => setOpen(true)}
          className="w-full flex items-center gap-3 p-2.5 rounded-xl border-2 border-[#1a5276] bg-[#1a5276]/5 text-left transition-all"
        >
          <HardwareIcon size={40} />
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
          + Selecionar {labelLower}
        </button>
      )}

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40"
          onClick={(e) => { if (e.target === e.currentTarget) setOpen(false) }}
        >
          <div className="w-full sm:max-w-lg bg-white rounded-t-2xl sm:rounded-2xl shadow-xl flex flex-col max-h-[90vh] sm:max-h-[80vh]">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 shrink-0">
              <span className="text-sm font-semibold text-gray-700">Escolher {labelLower}</span>
              <button
                onClick={() => setOpen(false)}
                className="text-gray-300 hover:text-gray-500 text-xl leading-none"
              >
                ×
              </button>
            </div>

            {/* Search + filters */}
            <div className="px-4 py-3 space-y-2 border-b border-gray-100 shrink-0">
              <input
                type="text"
                placeholder="Buscar por nome…"
                value={filtros.busca}
                onChange={(e) => setFiltro('busca', e.target.value)}
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-[#1a5276]/50"
              />
              <div className="flex gap-2 flex-wrap">
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
                {filtrosData && filtrosData.subtipos.length > 0 && (
                  <select
                    value={filtros.subtipo}
                    onChange={(e) => setFiltro('subtipo', e.target.value)}
                    className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:border-[#1a5276]/50 bg-white text-gray-600"
                  >
                    <option value="">Todos tipos</option>
                    {filtrosData.subtipos.map((s) => (
                      <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                )}
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
                  Nenhum item encontrado
                </div>
              )}
              {!loading && ferragens.map((f) => (
                <button
                  key={f.id}
                  onClick={() => handleSelect(f)}
                  className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 text-left border-b border-gray-50 last:border-0 transition-colors"
                >
                  <HardwareIcon size={40} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-800 truncate">{f.nome_apresentacao}</p>
                    <p className="text-xs text-gray-400 truncate">
                      {f.fabricante_nome ?? f.fabricante_codigo ?? '—'}
                      {f.tipo && ` · ${f.tipo.replace(/_/g, ' ')}`}
                      {' · '}
                      <span className="font-mono">{f.codigo_normalizado}</span>
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
