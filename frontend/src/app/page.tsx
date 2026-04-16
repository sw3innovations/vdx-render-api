'use client'

import { useEffect, useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { fetchTipologias } from '@/lib/api'
import { categoriaFromChave } from '@/lib/utils'
import type { Tipologia } from '@/lib/types'
import TipologiaCard, { TipologiaCardSkeleton } from '@/components/tipologia-card'

const TABS = ['Todos', 'Portas', 'Janelas', 'Box', 'Outros'] as const
type Tab = (typeof TABS)[number]

export default function HomePage() {
  const router = useRouter()
  const [tipologias, setTipologias] = useState<Tipologia[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [activeTab, setActiveTab] = useState<Tab>('Todos')

  useEffect(() => {
    fetchTipologias(1, 100)
      .then((res) => {
        setTipologias(res.items)
        setLoading(false)
      })
      .catch((err) => {
        setError(String(err))
        setLoading(false)
      })
  }, [])

  const filtered = useMemo(() => {
    return tipologias.filter((t) => {
      const categoria = t.categoria ?? categoriaFromChave(t.chave)
      const matchesTab = activeTab === 'Todos' || categoria === activeTab
      const matchesSearch =
        !search ||
        t.chave.toLowerCase().includes(search.toLowerCase()) ||
        (t.nome ?? '').toLowerCase().includes(search.toLowerCase())
      return matchesTab && matchesSearch
    })
  }, [tipologias, activeTab, search])

  return (
    <div className="min-h-screen bg-[#F5F2EE]">
      {/* Header */}
      <header className="bg-[#1a5276] text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">VDX Glass Engine</h1>
            <p className="text-blue-200 text-sm mt-0.5">
              Configurador de esquadrias de vidro — visualização 3D fotorrealista
            </p>
          </div>
          <div className="text-blue-200 text-xs opacity-70 hidden sm:block">
            {tipologias.length > 0 && `${tipologias.length} tipologias disponíveis`}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        {/* Search + Tabs */}
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="search"
            placeholder="Buscar tipologia…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1a5276]/30 focus:border-[#1a5276]/50 shadow-sm"
          />
        </div>

        {/* Tab filters */}
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`shrink-0 px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                activeTab === tab
                  ? 'bg-[#1a5276] text-white shadow-sm'
                  : 'bg-white text-gray-600 border border-gray-200 hover:border-[#1a5276]/40'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Error state */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
            <strong>Erro ao carregar tipologias:</strong> {error}
          </div>
        )}

        {/* Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {loading
            ? Array.from({ length: 8 }).map((_, i) => <TipologiaCardSkeleton key={i} />)
            : filtered.map((t) => (
                <TipologiaCard
                  key={t.chave}
                  tipologia={t}
                  onClick={() => router.push(`/configurar/${t.chave}`)}
                />
              ))}
        </div>

        {/* Empty state */}
        {!loading && filtered.length === 0 && !error && (
          <div className="text-center py-16 text-gray-400">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.5}
              className="w-12 h-12 mx-auto mb-3 opacity-40"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            <p className="text-sm">Nenhuma tipologia encontrada para "{search}"</p>
          </div>
        )}
      </main>
    </div>
  )
}
