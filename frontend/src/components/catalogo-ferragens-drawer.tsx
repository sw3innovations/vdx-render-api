'use client'

import { useEffect, useState, useMemo } from 'react'
import {
  listarCanonicalsV2,
  listarFiltrosV2,
  type CanonicalV2,
} from '@/lib/canonical-api'

const CATEGORIA_LABELS: Record<string, string> = {
  suporte:         'Suporte',
  dobradica:       'Dobradiça',
  contra_fechadura:'Contra-Fechadura',
  trinco:          'Trinco',
  fechadura:       'Fechadura',
  puxador:         'Puxador',
}

function categLabel(c: string): string {
  return CATEGORIA_LABELS[c] ?? c.replace(/_/g, ' ')
}

// ── Item card — Sub-Entrega 3 will wrap this with useDraggable ────────────────

interface ItemFerragemCardProps {
  canonical: CanonicalV2
  onSelect?: (c: CanonicalV2) => void
}

export function ItemFerragemCard({ canonical, onSelect }: ItemFerragemCardProps) {
  return (
    <button
      className="w-full text-left rounded-lg border border-gray-200 hover:border-[#1a5276] hover:bg-blue-50 p-3 transition-colors group"
      onClick={() => onSelect?.(canonical)}
      data-canonical-id={canonical.canonical_id}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-800 leading-tight truncate">
            {canonical.nome_apresentacao}
          </p>
          {canonical.subcategoria && (
            <p className="text-xs text-gray-400 mt-0.5 truncate">{canonical.subcategoria}</p>
          )}
        </div>
        <span className="shrink-0 text-[10px] font-mono bg-gray-100 group-hover:bg-white text-gray-500 px-1.5 py-0.5 rounded">
          {canonical.canonical_id}
        </span>
      </div>
      <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
        {canonical.categoria && (
          <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full">
            {categLabel(canonical.categoria)}
          </span>
        )}
        {canonical.linha && (
          <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full">
            {canonical.linha.replace(/_/g, ' ')}
          </span>
        )}
        {canonical.confidence === 'baixo' && (
          <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full">
            conf. baixa
          </span>
        )}
      </div>
    </button>
  )
}

// ── Drawer ────────────────────────────────────────────────────────────────────

interface Props {
  onClose: () => void
  onSelectItem?: (canonical: CanonicalV2) => void
}

export default function CatalogoFerragensDrawer({ onClose, onSelectItem }: Props) {
  const [categorias, setCategorias] = useState<string[]>([])
  const [items, setItems] = useState<CanonicalV2[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busca, setBusca] = useState('')
  const [categoriaAtiva, setCategoriaAtiva] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    Promise.all([listarFiltrosV2(), listarCanonicalsV2()])
      .then(([filtros, data]) => {
        setCategorias(filtros.categorias)
        setItems(data.canonicals)
        setError(null)
      })
      .catch(() => setError('Erro ao carregar catálogo'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const itemsFiltrados = useMemo(() => {
    let result = items
    if (categoriaAtiva) {
      result = result.filter((c) => c.categoria === categoriaAtiva)
    }
    if (busca.trim()) {
      const q = busca.trim().toLowerCase()
      result = result.filter(
        (c) =>
          c.canonical_id.toLowerCase().includes(q) ||
          c.nome_apresentacao.toLowerCase().includes(q) ||
          c.categoria?.toLowerCase().includes(q) ||
          c.subcategoria?.toLowerCase().includes(q)
      )
    }
    return result
  }, [items, categoriaAtiva, busca])

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30"
        onClick={onClose}
        aria-hidden
      />

      {/* Drawer panel */}
      <aside className="fixed inset-y-0 left-0 z-50 flex flex-col w-80 max-w-[90vw] bg-white shadow-2xl">
        {/* Header */}
        <div className="bg-[#1a5276] text-white px-4 py-3 flex items-center justify-between shrink-0">
          <div>
            <h2 className="font-semibold text-sm">Catálogo de Ferragens</h2>
            {!loading && (
              <p className="text-xs text-blue-200 mt-0.5">{items.length} itens</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-blue-200 hover:text-white text-xl leading-none ml-2"
            aria-label="Fechar catálogo"
          >
            ×
          </button>
        </div>

        {/* Search */}
        <div className="px-3 py-2 border-b border-gray-100 shrink-0">
          <input
            type="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por nome ou código…"
            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:border-[#1a5276]"
            autoFocus
          />
        </div>

        {/* Category pills */}
        {categorias.length > 0 && (
          <div className="px-3 py-2 flex gap-1.5 flex-wrap border-b border-gray-100 shrink-0">
            <button
              onClick={() => setCategoriaAtiva(null)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                categoriaAtiva === null
                  ? 'bg-[#1a5276] text-white border-[#1a5276]'
                  : 'border-gray-300 text-gray-600 hover:border-[#1a5276]'
              }`}
            >
              Todas
            </button>
            {categorias.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategoriaAtiva(cat === categoriaAtiva ? null : cat)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  categoriaAtiva === cat
                    ? 'bg-[#1a5276] text-white border-[#1a5276]'
                    : 'border-gray-300 text-gray-600 hover:border-[#1a5276]'
                }`}
              >
                {categLabel(cat)}
              </button>
            ))}
          </div>
        )}

        {/* Results count */}
        {!loading && !error && (
          <div className="px-3 py-1 shrink-0">
            <p className="text-xs text-gray-400">
              {itemsFiltrados.length} resultado{itemsFiltrados.length !== 1 ? 's' : ''}
              {(busca || categoriaAtiva) ? ' (filtrado)' : ''}
            </p>
          </div>
        )}

        {/* List */}
        <div className="flex-1 overflow-y-auto px-3 py-2 flex flex-col gap-2">
          {loading && (
            <div className="flex items-center justify-center h-32 text-gray-400 text-sm">
              Carregando…
            </div>
          )}
          {error && (
            <div className="flex items-center justify-center h-32 text-red-500 text-sm text-center px-4">
              {error}
            </div>
          )}
          {!loading && !error && itemsFiltrados.length === 0 && (
            <div className="flex items-center justify-center h-32 text-gray-400 text-sm text-center px-4">
              Nenhuma ferragem encontrada
            </div>
          )}
          {!loading && !error && itemsFiltrados.map((c) => (
            <ItemFerragemCard
              key={c.canonical_id}
              canonical={c}
              onSelect={onSelectItem}
            />
          ))}
        </div>
      </aside>
    </>
  )
}
