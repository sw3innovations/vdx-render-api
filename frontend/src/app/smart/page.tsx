'use client'

import { useState, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import { photoToProject, sketchToProject, textToProject, resizeImageToBase64 } from '@/lib/api'
import type { SmartProjectResponse, SceneJSON } from '@/lib/types'

const Viewer3D = dynamic(() => import('@/components/viewer-3d'), { ssr: false })

type Tab = 'foto' | 'croqui' | 'texto'

const TABS: { id: Tab; label: string; hint: string }[] = [
  { id: 'foto', label: '📸 Foto', hint: 'Foto real do vão' },
  { id: 'croqui', label: '✏️ Croqui', hint: 'Desenho a mão' },
  { id: 'texto', label: '💬 Texto', hint: 'Descrição verbal' },
]

export default function SmartPage() {
  const router = useRouter()
  const [tab, setTab] = useState<Tab>('foto')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [descricao, setDescricao] = useState('')
  const [fabricante, setFabricante] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<SmartProjectResponse | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback((f: File) => {
    setFile(f)
    setError(null)
    setResult(null)
    const objectUrl = URL.createObjectURL(f)
    setPreview(objectUrl)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const f = e.dataTransfer.files[0]
      if (f && f.type.startsWith('image/')) handleFile(f)
    },
    [handleFile]
  )

  const switchTab = (t: Tab) => {
    setTab(t)
    setResult(null)
    setError(null)
  }

  const handleAnalyze = async () => {
    setError(null)
    setLoading(true)
    setResult(null)
    try {
      let res: SmartProjectResponse
      if (tab === 'texto') {
        if (!descricao.trim()) throw new Error('Descreva o projeto antes de analisar')
        res = await textToProject({ descricao: descricao.trim(), fabricante: fabricante || undefined })
      } else {
        if (!file) throw new Error('Selecione uma imagem antes de analisar')
        const image_base64 = await resizeImageToBase64(file)
        if (tab === 'foto') {
          res = await photoToProject({ image_base64 })
        } else {
          res = await sketchToProject({ image_base64 })
        }
      }
      setResult(res)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  const canAnalyze = tab === 'texto' ? descricao.trim().length > 0 : file !== null

  return (
    <div className="min-h-screen bg-[#F5F2EE]">
      <header className="bg-[#1a5276] text-white shadow-lg">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-5 flex items-center gap-4">
          <button
            onClick={() => router.push('/')}
            className="text-blue-200 hover:text-white transition-colors text-sm font-medium"
          >
            ← Voltar
          </button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Smart Vision</h1>
            <p className="text-blue-200 text-sm mt-0.5">
              Foto, croqui ou descrição → projeto 3D completo com ferragens
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        {/* Tab switcher */}
        <div className="flex gap-1.5 bg-white rounded-2xl p-1.5 shadow-sm border border-gray-100 w-fit">
          {TABS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => switchTab(id)}
              className={`px-5 py-2 rounded-xl text-sm font-medium transition-all ${
                tab === id
                  ? 'bg-[#1a5276] text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Input panel */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
          {tab !== 'texto' ? (
            <>
              <div
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center cursor-pointer hover:border-[#1a5276]/40 hover:bg-blue-50/20 transition-all select-none"
              >
                {preview ? (
                  <img
                    src={preview}
                    alt="preview"
                    className="max-h-64 mx-auto rounded-lg object-contain"
                  />
                ) : (
                  <div className="space-y-2">
                    <div className="text-4xl">{tab === 'foto' ? '📸' : '✏️'}</div>
                    <p className="text-sm text-gray-500">
                      {tab === 'foto'
                        ? 'Arraste uma foto do vão ou clique para selecionar'
                        : 'Arraste um croqui ou clique para selecionar'}
                    </p>
                    <p className="text-xs text-gray-300">JPG, PNG, WEBP — redimensionado automaticamente</p>
                  </div>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) handleFile(e.target.files[0])
                }}
              />
              {file && (
                <p className="text-xs text-gray-400 text-center truncate">{file.name}</p>
              )}
            </>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">
                  Descrição do projeto
                </label>
                <textarea
                  value={descricao}
                  onChange={(e) => setDescricao(e.target.value)}
                  placeholder="Ex: porta pivotante dupla em vidro fumê 10mm, 1400×2200mm, com puxador inox..."
                  rows={4}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a5276]/30 resize-none"
                />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">
                  Fabricante{' '}
                  <span className="text-gray-400 font-normal">(opcional)</span>
                </label>
                <input
                  type="text"
                  value={fabricante}
                  onChange={(e) => setFabricante(e.target.value)}
                  placeholder="Nome do fabricante..."
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a5276]/30"
                />
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
              {error}
            </div>
          )}

          <button
            onClick={handleAnalyze}
            disabled={loading || !canAnalyze}
            className="w-full bg-[#1a5276] hover:bg-[#1a5276]/90 disabled:opacity-40 text-white font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Analisando…
              </>
            ) : (
              '✨ Gerar projeto'
            )}
          </button>
        </div>

        {/* Result */}
        {result && (
          <div className="space-y-4">
            {/* Analysis card */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-bold text-gray-900">Análise Smart Vision</h2>
                <span className="text-xs bg-green-50 text-green-700 border border-green-200 px-2.5 py-1 rounded-full font-medium">
                  {Math.round(result.analise.confianca * 100)}% confiança
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {(
                  [
                    { label: 'Tipologia', value: result.analise.tipologia_sugerida },
                    { label: 'Largura', value: `${result.analise.largura_mm} mm` },
                    { label: 'Altura', value: `${result.analise.altura_mm} mm` },
                    { label: 'Folhas', value: String(result.analise.num_folhas) },
                    { label: 'Espessura', value: `${result.analise.espessura_vidro_mm} mm` },
                    { label: 'Cor vidro', value: result.analise.cor_vidro },
                  ] as { label: string; value: string }[]
                ).map(({ label, value }) => (
                  <div key={label} className="bg-gray-50 rounded-xl p-3">
                    <p className="text-xs text-gray-400 mb-0.5">{label}</p>
                    <p className="text-sm font-semibold text-gray-800 truncate">{value}</p>
                  </div>
                ))}
              </div>
              {result.analise.observacoes && (
                <p className="text-xs text-gray-500 mt-3 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
                  {result.analise.observacoes}
                </p>
              )}
              <p className="text-xs text-gray-300 mt-2 font-mono">
                engine: {result.engine}
              </p>
            </div>

            {/* 3D Viewer */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="h-[420px]">
                <Viewer3D scene={result.scene as SceneJSON} className="w-full h-full" />
              </div>
            </div>

            {/* Ferragens */}
            {result.ferragens.length > 0 && (
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
                <h3 className="text-sm font-bold text-gray-700 mb-3">
                  Ferragens ({result.ferragens.length})
                </h3>
                <ul className="space-y-1.5">
                  {result.ferragens.map((f: Record<string, unknown>, i: number) => (
                    <li key={i} className="flex items-center gap-2 text-xs text-gray-600">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#1a5276]/40 shrink-0" />
                      <span className="font-medium">{String(f.nome ?? '')}</span>
                      {f.codigo ? (
                        <span className="text-gray-400 font-mono">#{String(f.codigo)}</span>
                      ) : null}
                      {f.peca ? (
                        <span className="text-gray-300">— {String(f.peca)}</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pb-8">
              <button
                onClick={() => router.push(`/configurar/${result.tipologia_chave}`)}
                className="flex-1 bg-[#1a5276] hover:bg-[#1a5276]/90 text-white font-semibold py-3 rounded-xl transition-all"
              >
                Configurar este projeto →
              </button>
              <button
                onClick={() => {
                  setResult(null)
                  setFile(null)
                  setPreview(null)
                  setDescricao('')
                }}
                className="px-5 py-3 rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 text-sm font-medium transition-all"
              >
                Nova análise
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
