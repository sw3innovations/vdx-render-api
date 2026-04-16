'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import { fetchScene, fetchRender, exportPng, exportPdf, downloadBlob } from '@/lib/api'
import { tipologiaLabel, formatDim } from '@/lib/utils'
import type { SceneJSON, FerragemInfo } from '@/lib/types'

// Dynamic import to avoid SSR issues with Three.js
const Viewer3D = dynamic(() => import('@/components/viewer-3d'), { ssr: false })

const COR_VIDRO_OPTIONS = [
  { value: 'incolor', label: 'Incolor', color: '#E8F4FD' },
  { value: 'verde', label: 'Verde', color: '#A8D5A2' },
  { value: 'fume', label: 'Fumê', color: '#708090' },
  { value: 'bronze', label: 'Bronze', color: '#CD7F32' },
  { value: 'espelho', label: 'Espelho', color: '#C0C0C0' },
]

const ESPESSURA_OPTIONS = [6, 8, 10, 12] as const

export default function ConfigurarPage() {
  const params = useParams()
  const router = useRouter()
  const tipologia = String(params.tipologia)

  const [largura, setLargura] = useState(900)
  const [altura, setAltura] = useState(2100)
  const [espessura, setEspessura] = useState<number>(8)
  const [corVidro, setCorVidro] = useState('incolor')
  const [scene, setScene] = useState<SceneJSON | null>(null)
  const [ferragens, setFerragens] = useState<FerragemInfo[]>([])
  const [loadingScene, setLoadingScene] = useState(false)
  const [loadingExport, setLoadingExport] = useState<'png' | 'pdf' | null>(null)
  const [error, setError] = useState<string | null>(null)

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const loadScene = useCallback(
    async (larg: number, alt: number, cor: string, esp: number) => {
      setLoadingScene(true)
      setError(null)
      try {
        const [sceneData, renderData] = await Promise.all([
          fetchScene(tipologia, larg, alt, cor, esp),
          fetchRender(tipologia, larg, alt, cor, esp),
        ])
        setScene(sceneData)
        // Collect all ferragens from all peças
        const allFerragens = renderData.pecas.flatMap((p) => p.ferragens)
        setFerragens(allFerragens)
      } catch (err) {
        setError(String(err))
      } finally {
        setLoadingScene(false)
      }
    },
    [tipologia]
  )

  // Initial load
  useEffect(() => {
    loadScene(largura, altura, corVidro, espessura)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Debounced reload on param changes
  const triggerReload = useCallback(
    (larg: number, alt: number, cor: string, esp: number) => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => loadScene(larg, alt, cor, esp), 300)
    },
    [loadScene]
  )

  const handleLargura = (v: number) => {
    setLargura(v)
    triggerReload(v, altura, corVidro, espessura)
  }
  const handleAltura = (v: number) => {
    setAltura(v)
    triggerReload(largura, v, corVidro, espessura)
  }
  const handleEspessura = (v: number) => {
    setEspessura(v)
    triggerReload(largura, altura, corVidro, v)
  }
  const handleCorVidro = (v: string) => {
    setCorVidro(v)
    triggerReload(largura, altura, v, espessura)
  }

  const handleExportPng = async () => {
    setLoadingExport('png')
    try {
      const blob = await exportPng(tipologia, largura, altura, corVidro, espessura)
      downloadBlob(blob, `${tipologia}_${largura}x${altura}.png`)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoadingExport(null)
    }
  }

  const handleExportPdf = async () => {
    setLoadingExport('pdf')
    try {
      const blob = await exportPdf(tipologia, largura, altura, corVidro, espessura)
      downloadBlob(blob, `${tipologia}_${largura}x${altura}.pdf`)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoadingExport(null)
    }
  }

  const handleWhatsApp = () => {
    const data = { tipologia, largura, altura, corVidro }
    const encoded = btoa(JSON.stringify(data))
    const url = `${window.location.origin}/compartilhar/${encoded}`
    const text = `Veja esta peça de vidro: ${url}`
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank')
  }

  const label = tipologiaLabel(tipologia)

  return (
    <div className="flex flex-col md:flex-row h-screen bg-[#F5F2EE] overflow-hidden">
      {/* ── Side Panel ─────────────────────────────────────────────────────── */}
      <aside className="w-full md:w-72 lg:w-80 bg-white border-r border-gray-200 flex flex-col overflow-y-auto shrink-0 md:h-screen">
        {/* Header */}
        <div className="px-5 pt-5 pb-4 border-b border-gray-100">
          <button
            onClick={() => router.push('/')}
            className="flex items-center gap-1.5 text-sm text-[#1a5276] hover:text-[#1a5276]/70 font-medium mb-3 transition-colors"
          >
            <span>←</span> Voltar
          </button>
          <h1 className="text-lg font-bold text-gray-900 leading-tight">{label}</h1>
          <p className="text-xs text-gray-400 font-mono mt-0.5">{tipologia}</p>
        </div>

        <div className="flex-1 px-5 py-4 space-y-6">
          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-3 py-2 text-xs">
              {error}
            </div>
          )}

          {/* Largura */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-sm font-semibold text-gray-700">Largura</label>
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  value={largura}
                  min={300}
                  max={3000}
                  step={50}
                  onChange={(e) => handleLargura(Number(e.target.value))}
                  className="w-20 text-right text-sm border border-gray-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-1 focus:ring-[#1a5276]/40"
                />
                <span className="text-xs text-gray-400">mm</span>
              </div>
            </div>
            <input
              type="range"
              min={300}
              max={3000}
              step={50}
              value={largura}
              onChange={(e) => handleLargura(Number(e.target.value))}
              className="w-full accent-[#1a5276]"
            />
            <div className="flex justify-between text-xs text-gray-300">
              <span>300</span>
              <span>3000 mm</span>
            </div>
          </div>

          {/* Altura */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-sm font-semibold text-gray-700">Altura</label>
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  value={altura}
                  min={600}
                  max={4000}
                  step={50}
                  onChange={(e) => handleAltura(Number(e.target.value))}
                  className="w-20 text-right text-sm border border-gray-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-1 focus:ring-[#1a5276]/40"
                />
                <span className="text-xs text-gray-400">mm</span>
              </div>
            </div>
            <input
              type="range"
              min={600}
              max={4000}
              step={50}
              value={altura}
              onChange={(e) => handleAltura(Number(e.target.value))}
              className="w-full accent-[#1a5276]"
            />
            <div className="flex justify-between text-xs text-gray-300">
              <span>600</span>
              <span>4000 mm</span>
            </div>
          </div>

          {/* Espessura */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-700">Espessura do Vidro</label>
            <div className="flex gap-2">
              {ESPESSURA_OPTIONS.map((v) => (
                <button
                  key={v}
                  onClick={() => handleEspessura(v)}
                  className={`flex-1 py-1.5 rounded-lg text-sm font-medium border transition-all ${
                    espessura === v
                      ? 'bg-[#1a5276] text-white border-[#1a5276]'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-[#1a5276]/40'
                  }`}
                >
                  {v}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-400 text-center">{formatDim(espessura)} de espessura</p>
          </div>

          {/* Cor do Vidro */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-700">Cor do Vidro</label>
            <div className="flex gap-2 flex-wrap">
              {COR_VIDRO_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => handleCorVidro(opt.value)}
                  title={opt.label}
                  className={`flex flex-col items-center gap-1 transition-all ${
                    corVidro === opt.value ? 'opacity-100' : 'opacity-50 hover:opacity-80'
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-full border-2 transition-all ${
                      corVidro === opt.value ? 'border-[#1a5276] scale-110' : 'border-gray-200'
                    }`}
                    style={{ background: opt.color }}
                  />
                  <span className="text-[10px] text-gray-500">{opt.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Ferragens */}
          {ferragens.length > 0 && (
            <div className="space-y-2">
              <label className="text-sm font-semibold text-gray-700">
                Ferragens ({ferragens.length})
              </label>
              <ul className="space-y-1">
                {ferragens.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                    <span className="text-gray-300 mt-0.5">•</span>
                    <span>
                      <span className="font-medium">{f.nome}</span>
                      {f.codigo && (
                        <span className="text-gray-400 font-mono ml-1">#{f.codigo}</span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="px-5 py-4 border-t border-gray-100 space-y-2">
          <div className="flex gap-2">
            <button
              onClick={handleExportPng}
              disabled={loadingExport !== null || loadingScene}
              className="flex-1 bg-[#1a5276] hover:bg-[#1a5276]/90 disabled:opacity-50 text-white text-sm font-medium py-2.5 rounded-xl transition-all"
            >
              {loadingExport === 'png' ? '⏳' : '⬇'} PNG
            </button>
            <button
              onClick={handleExportPdf}
              disabled={loadingExport !== null || loadingScene}
              className="flex-1 bg-white hover:bg-gray-50 disabled:opacity-50 text-[#1a5276] border border-[#1a5276]/30 text-sm font-medium py-2.5 rounded-xl transition-all"
            >
              {loadingExport === 'pdf' ? '⏳' : '⬇'} PDF
            </button>
          </div>
          <button
            onClick={handleWhatsApp}
            className="w-full bg-[#25D366] hover:bg-[#25D366]/90 text-white text-sm font-medium py-2.5 rounded-xl flex items-center justify-center gap-2 transition-all"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
            </svg>
            Compartilhar no WhatsApp
          </button>
        </div>
      </aside>

      {/* ── 3D Viewer ───────────────────────────────────────────────────────── */}
      <main className="flex-1 relative min-h-[50vh] md:min-h-0">
        {loadingScene && !scene && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/60 z-10 text-white gap-3">
            <div className="w-8 h-8 border-4 border-white/20 border-t-white rounded-full animate-spin" />
            <span className="text-sm">Carregando…</span>
          </div>
        )}

        {loadingScene && scene && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 bg-black/50 backdrop-blur-sm text-white text-xs px-3 py-1.5 rounded-full">
            Atualizando cena…
          </div>
        )}

        <Viewer3D
          scene={scene}
          className="w-full h-full"
        />

        {/* Dimensions overlay */}
        {scene && (
          <div className="absolute bottom-4 left-4 bg-black/40 backdrop-blur-sm text-white text-xs px-3 py-1.5 rounded-lg font-mono">
            {formatDim(largura)} × {formatDim(altura)} × {espessura}mm
          </div>
        )}
      </main>
    </div>
  )
}
