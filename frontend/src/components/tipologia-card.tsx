'use client'

import { useState } from 'react'
import type { Tipologia } from '@/lib/types'
import { tipologiaLabel, categoriaFromChave, cn } from '@/lib/utils'

const CATEGORY_COLORS: Record<string, string> = {
  Portas: 'bg-blue-100 text-blue-800',
  Janelas: 'bg-green-100 text-green-800',
  Box: 'bg-purple-100 text-purple-800',
  Outros: 'bg-gray-100 text-gray-700',
}

interface TipologiaCardProps {
  tipologia: Tipologia
  onClick: () => void
}

export default function TipologiaCard({ tipologia, onClick }: TipologiaCardProps) {
  const [imgError, setImgError] = useState(false)
  const [imgLoaded, setImgLoaded] = useState(false)

  const categoria = tipologia.categoria ?? categoriaFromChave(tipologia.chave)
  const label = tipologia.nome || tipologiaLabel(tipologia.chave)
  const previewUrl = `/api/vdx/v1/tipologia/${encodeURIComponent(tipologia.chave)}/fotorrealista`

  return (
    <button
      onClick={onClick}
      className={cn(
        'group relative flex flex-col bg-white rounded-2xl overflow-hidden shadow-sm',
        'border border-gray-100 hover:border-[#1a5276]/40 hover:shadow-lg',
        'transition-all duration-200 text-left cursor-pointer'
      )}
    >
      {/* Preview image */}
      <div className="relative w-full aspect-[4/3] bg-gray-50 overflow-hidden">
        {!imgLoaded && !imgError && (
          <div className="absolute inset-0 animate-pulse bg-gradient-to-br from-gray-100 to-gray-200" />
        )}

        {!imgError ? (
          <img
            src={previewUrl}
            alt={label}
            className={cn(
              'w-full h-full object-contain p-4 transition-transform duration-300 group-hover:scale-105',
              imgLoaded ? 'opacity-100' : 'opacity-0'
            )}
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-300 gap-2">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.5}
              className="w-10 h-10"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M3 9h18M9 21V9" />
            </svg>
            <span className="text-xs">Sem preview</span>
          </div>
        )}

        {/* Hover overlay */}
        <div className="absolute inset-0 bg-[#1a5276]/0 group-hover:bg-[#1a5276]/5 transition-colors duration-200" />
      </div>

      {/* Card body */}
      <div className="p-3 flex-1 flex flex-col gap-1">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-semibold text-gray-800 leading-tight line-clamp-2">{label}</p>
          <span
            className={cn(
              'shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full',
              CATEGORY_COLORS[categoria] ?? CATEGORY_COLORS['Outros']
            )}
          >
            {categoria}
          </span>
        </div>
        <p className="text-xs text-gray-400 font-mono truncate">{tipologia.chave}</p>
      </div>

      {/* Bottom CTA */}
      <div className="px-3 pb-3">
        <div className="w-full bg-[#1a5276]/0 group-hover:bg-[#1a5276] text-[#1a5276] group-hover:text-white text-xs font-medium text-center py-1.5 rounded-lg border border-[#1a5276]/30 group-hover:border-transparent transition-all duration-200">
          Configurar →
        </div>
      </div>
    </button>
  )
}

// ── Skeleton card ─────────────────────────────────────────────────────────────

export function TipologiaCardSkeleton() {
  return (
    <div className="flex flex-col bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-100">
      <div className="w-full aspect-[4/3] animate-pulse bg-gradient-to-br from-gray-100 to-gray-200" />
      <div className="p-3 flex flex-col gap-2">
        <div className="flex justify-between gap-2">
          <div className="h-4 bg-gray-200 rounded animate-pulse flex-1" />
          <div className="h-4 w-12 bg-gray-100 rounded-full animate-pulse" />
        </div>
        <div className="h-3 w-2/3 bg-gray-100 rounded animate-pulse" />
      </div>
      <div className="px-3 pb-3">
        <div className="h-7 bg-gray-100 rounded-lg animate-pulse" />
      </div>
    </div>
  )
}
