'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import { fetchScene } from '@/lib/api'
import { tipologiaLabel, formatDim } from '@/lib/utils'
import type { SceneJSON } from '@/lib/types'

const Viewer3D = dynamic(() => import('@/components/viewer-3d'), { ssr: false })

interface ShareData {
  tipologia: string
  largura: number
  altura: number
  corVidro: string
}

export default function ShareClient({ data }: { data: ShareData }) {
  const { tipologia, largura, altura, corVidro } = data
  const [scene, setScene] = useState<SceneJSON | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchScene(tipologia, largura, altura, corVidro)
      .then(setScene)
      .catch((err) => setError(String(err)))
  }, [tipologia, largura, altura, corVidro])

  const label = tipologiaLabel(tipologia)

  return (
    <div className="min-h-screen flex flex-col bg-[#F5F2EE]">
      {/* Header */}
      <header className="bg-[#1a5276] text-white px-6 py-4 flex items-center justify-between shadow-lg shrink-0">
        <div>
          <h1 className="font-bold text-lg">{label}</h1>
          <p className="text-blue-200 text-sm">
            {formatDim(largura)} × {formatDim(altura)} · vidro {corVidro}
          </p>
        </div>
        <Link
          href={`/configurar/${tipologia}`}
          className="bg-white text-[#1a5276] text-sm font-semibold px-4 py-2 rounded-xl hover:bg-blue-50 transition-colors"
        >
          Personalizar →
        </Link>
      </header>

      {/* Viewer */}
      <main className="flex-1 relative min-h-[400px]">
        {error && (
          <div className="absolute inset-0 flex items-center justify-center text-red-500 text-sm px-4 text-center">
            Erro ao carregar: {error}
          </div>
        )}
        <Viewer3D scene={scene} className="w-full h-full" />
      </main>

      {/* Footer */}
      <footer className="text-center text-xs text-gray-400 py-3 shrink-0">
        Criado com{' '}
        <a href="/" className="text-[#1a5276] hover:underline">
          VDX Glass Engine
        </a>
      </footer>
    </div>
  )
}
