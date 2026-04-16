'use client'

import { useEffect, useState, useCallback, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import dynamic from 'next/dynamic'
import { fetchScene } from '@/lib/api'
import type { SceneJSON } from '@/lib/types'

const Viewer3D = dynamic(() => import('@/components/viewer-3d'), { ssr: false })

function WidgetInner() {
  const searchParams = useSearchParams()
  const tipologia = searchParams.get('tipologia') ?? 'porta_pivotante_simples'
  const largura = Number(searchParams.get('largura') ?? 900)
  const altura = Number(searchParams.get('altura') ?? 2100)
  const cor = searchParams.get('cor') ?? 'incolor'
  // Note: 'key' param is informational; actual auth uses NEXT_PUBLIC_VDX_KEY
  const [scene, setScene] = useState<SceneJSON | null>(null)
  const [isAnimating, setIsAnimating] = useState(false)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    fetchScene(tipologia, largura, altura, cor).then(setScene).catch(console.error)
  }, [tipologia, largura, altura, cor])

  // PostMessage: send ready event
  const handleReady = useCallback(() => {
    setReady(true)
    window.parent?.postMessage(
      { type: 'vdx:ready', tipologia, dimensoes: { largura, altura } },
      '*'
    )
  }, [tipologia, largura, altura])

  // PostMessage: listen for update events
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data?.type === 'vdx:update') {
        const { tipologia: t, largura: l, altura: a, cor: c } = event.data
        if (t && l && a) {
          fetchScene(t, l, a, c ?? 'incolor').then(setScene).catch(console.error)
        }
      }
    }
    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
  }, [])

  const hasAnimation = scene?.vidros.some(
    (v) => v.animacao && v.animacao.tipo !== 'fixo'
  ) ?? false

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-gray-900">
      <Viewer3D scene={scene} className="w-full h-full" onReady={handleReady} />

      {/* Minimal animation overlay */}
      {ready && hasAnimation && (
        <button
          onClick={() => setIsAnimating((p) => !p)}
          className="absolute bottom-3 right-3 bg-white/10 hover:bg-white/20 backdrop-blur-sm border border-white/20 text-white px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
        >
          {isAnimating ? '⏸ Fechar' : '▶ Abrir'}
        </button>
      )}

      {/* Watermark */}
      <div className="absolute bottom-3 left-3 text-white/30 text-[10px] font-mono pointer-events-none">
        VDX Glass Engine
      </div>
    </div>
  )
}

export default function WidgetPage() {
  return (
    <Suspense fallback={<div className="w-screen h-screen bg-gray-900" />}>
      <WidgetInner />
    </Suspense>
  )
}
