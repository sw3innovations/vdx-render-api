'use client'

import { useEffect, useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { fetchCanonicalTipologias, type TipologiaCanonica } from '@/lib/canonical-api'
import { categoriaCanToTab, CanonicalTipologiaCard } from '@/components/tipologia-card'
import { TipologiaCardSkeleton } from '@/components/tipologia-card'

const TABS = ['Todos', 'Portas', 'Janelas', 'Box', 'Outros'] as const
type Tab = (typeof TABS)[number]

const TEST_CODE_RE = /^TIP_9[89]\d{2}_/

export default function HomePage() {
  const router = useRouter()
  const [tipologias, setTipologias] = useState<TipologiaCanonica[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [activeTab, setActiveTab] = useState<Tab>('Todos')

  useEffect(() => {
    fetchCanonicalTipologias(200)
      .then((res) => {
        // Exclude SEM_TIPOLOGIA and test fixture entries
        const filtered = res.tipologias.filter(
          (t) => t.codigo !== 'SEM_TIPOLOGIA' && !TEST_CODE_RE.test(t.codigo)
        )
        setTipologias(filtered)
        setLoading(false)
      })
      .catch((err) => {
        setError(String(err))
        setLoading(false)
      })
  }, [])

  const counts = useMemo(() => {
    const c: Record<Tab, number> = { Todos: 0, Portas: 0, Janelas: 0, Box: 0, Outros: 0 }
    for (const t of tipologias) {
      const cat = categoriaCanToTab(t.categoria) as Tab
      c['Todos']++
      c[cat]++
    }
    return c
  }, [tipologias])

  const filtered = useMemo(() => {
    const visible = tipologias.filter((t) => {
      const cat = categoriaCanToTab(t.categoria) as Tab
      const matchesTab = activeTab === 'Todos' || cat === activeTab
      const matchesSearch =
        !search ||
        t.codigo.toLowerCase().includes(search.toLowerCase()) ||
        t.nome_apresentacao.toLowerCase().includes(search.toLowerCase())
      return matchesTab && matchesSearch
    })
    // Renderizáveis primeiro, "em breve" no fim
    return [
      ...visible.filter((t) => t.tem_renderer),
      ...visible.filter((t) => !t.tem_renderer),
    ]
  }, [tipologias, activeTab, search])

  const totalCount = tipologias.length
  const rendererCount = tipologias.filter((t) => t.tem_renderer).length

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
          <div className="flex items-center gap-4">
            <Link
              href="/importar"
              className="hidden sm:flex items-center gap-1.5 text-sm bg-white/10 hover:bg-white/20 text-white px-3 py-1.5 rounded-lg transition-colors"
            >
              ↑ Importar JSON
            </Link>
            {!loading && (
              <div className="text-blue-200 text-xs opacity-70 hidden sm:block">
                {rendererCount} renderizáveis · {totalCount} total
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        {/* Search */}
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
              className={`shrink-0 flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                activeTab === tab
                  ? 'bg-[#1a5276] text-white shadow-sm'
                  : 'bg-white text-gray-600 border border-gray-200 hover:border-[#1a5276]/40'
              }`}
            >
              {tab}
              {!loading && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                  activeTab === tab ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-500'
                }`}>
                  {counts[tab]}
                </span>
              )}
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
                <CanonicalTipologiaCard
                  key={t.codigo}
                  tipologia={t}
                  onClick={t.tem_renderer ? () => router.push(`/configurar/${t.codigo}`) : undefined}
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
            <p className="text-sm">Nenhuma tipologia encontrada para &quot;{search}&quot;</p>
          </div>
        )}

        {/* CTA Smart Vision */}
        {!loading && !error && (
          <div className="mt-2 rounded-2xl bg-[#1a5276]/5 border border-[#1a5276]/15 px-5 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-[#1a5276]">Não encontrou o que precisa?</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Use o Smart Vision para criar um projeto a partir de uma foto, croqui ou descrição.
              </p>
            </div>
            <Link
              href="/smart"
              className="shrink-0 flex items-center gap-2 bg-[#1a5276] hover:bg-[#154360] text-white text-sm font-medium px-4 py-2 rounded-xl transition-colors"
            >
              ✨ Smart Vision
            </Link>
          </div>
        )}
      </main>
    </div>
  )
}
