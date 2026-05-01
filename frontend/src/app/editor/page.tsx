'use client'

import { useEffect, useRef, useState, useCallback, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import { useStore } from 'zustand'
import { useEditorStore, DEFAULT_TIPOLOGIA } from '@/stores/editor-store'
import type { TipologiaEditor, Painel } from '@/stores/editor-store'
import ModalAdicionarPainel from '@/components/modal-adicionar-painel'
import CatalogoFerragensDrawer from '@/components/catalogo-ferragens-drawer'

const EditorCanvas = dynamic(() => import('@/components/editor-canvas'), { ssr: false })

const GRID_OPTIONS = [1, 5, 10, 50] as const

function EditorPageInner() {
  const searchParams = useSearchParams()
  const tipologia = useEditorStore((s) => s.tipologia)
  const painelSelecionadoNome = useEditorStore((s) => s.painelSelecionadoNome)
  const gridSize = useEditorStore((s) => s.gridSize)
  const setTipologia = useEditorStore((s) => s.setTipologia)
  const setNome = useEditorStore((s) => s.setNome)
  const setGridSize = useEditorStore((s) => s.setGridSize)
  const setPainelSelecionado = useEditorStore((s) => s.setPainelSelecionado)
  const atualizarPainel = useEditorStore((s) => s.atualizarPainel)
  const adicionarPainel = useEditorStore((s) => s.adicionarPainel)

  const { undo, redo, pastStates, futureStates } = useStore(useEditorStore.temporal)
  const nomeRef = useRef<HTMLInputElement>(null)
  const [showProps, setShowProps] = useState(false)
  const [saving, setSaving] = useState(false)
  const [savedUrl, setSavedUrl] = useState<string | null>(null)
  const [showModalPainel, setShowModalPainel] = useState(false)
  const [showCatalogo, setShowCatalogo] = useState(false)

  const painelSelecionado = tipologia.paineis.find(
    (p) => p.nome === painelSelecionadoNome
  ) ?? null

  const proximaPosicaoX = tipologia.paineis.reduce(
    (acc, p) => Math.max(acc, (p.posicao_x_mm ?? 0) + p.largura_mm + 20),
    0
  )

  function handleAdicionarPainel(painel: Painel) {
    adicionarPainel(painel)
    setShowModalPainel(false)
    setPainelSelecionado(painel.nome)
  }

  useEffect(() => {
    const carregarChave = searchParams.get('carregar')
    const importChave = searchParams.get('import')
    if (carregarChave) {
      fetch(`/api/v1/editor/${carregarChave}`)
        .then((r) => r.json())
        .then((data) => {
          if (data.tipologia_json) setTipologia(data.tipologia_json as TipologiaEditor)
        })
        .catch(() => setTipologia(DEFAULT_TIPOLOGIA))
    } else if (importChave) {
      fetch(`/api/v1/import/${importChave}`)
        .then((r) => r.json())
        .then((data) => {
          if (data.tipologia_json) setTipologia(data.tipologia_json as TipologiaEditor)
        })
        .catch(() => setTipologia(DEFAULT_TIPOLOGIA))
    } else {
      setTipologia(DEFAULT_TIPOLOGIA)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSalvar = useCallback(async () => {
    setSaving(true)
    setSavedUrl(null)
    try {
      const resp = await fetch('/api/v1/editor/salvar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tipologia),
      })
      const data = await resp.json()
      const url = `${window.location.origin}${data.url}`
      setSavedUrl(url)
      try { await navigator.clipboard.writeText(url) } catch { /* ignore */ }
    } catch {
      // silently fail
    } finally {
      setSaving(false)
    }
  }, [tipologia])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey
      if (!mod) return
      if (e.key === 'z' && !e.shiftKey) { e.preventDefault(); undo() }
      if ((e.key === 'z' && e.shiftKey) || e.key === 'y') { e.preventDefault(); redo() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [undo, redo])

  useEffect(() => {
    if (painelSelecionado) setShowProps(true)
  }, [painelSelecionado])

  return (
    <div className="min-h-screen bg-[#F5F2EE] flex flex-col">
      {showModalPainel && (
        <ModalAdicionarPainel
          nomesExistentes={tipologia.paineis.map((p) => p.nome)}
          proximaPosicaoX={proximaPosicaoX}
          onConfirmar={handleAdicionarPainel}
          onCancelar={() => setShowModalPainel(false)}
        />
      )}

      {showCatalogo && (
        <CatalogoFerragensDrawer
          onClose={() => setShowCatalogo(false)}
        />
      )}

      {/* Header */}
      <header className="bg-[#1a5276] text-white shadow-lg shrink-0">
        <div className="max-w-full mx-auto px-3 sm:px-6 py-2.5 flex items-center justify-between gap-2">
          <input
            ref={nomeRef}
            value={tipologia.nome}
            onChange={(e) => setNome(e.target.value)}
            className="bg-transparent text-white font-bold text-sm sm:text-base border-b border-blue-400 focus:border-white outline-none min-w-0 w-32 sm:w-56 truncate"
            placeholder="Nome"
          />

          {/* Toolbar — hidden on xs, visible from sm */}
          <div className="hidden sm:flex items-center gap-1.5">
            <div className="flex items-center gap-1 text-xs text-blue-200">
              <span className="hidden md:inline">Grid:</span>
              {GRID_OPTIONS.map((g) => (
                <button
                  key={g}
                  onClick={() => setGridSize(g)}
                  className={`px-1.5 py-0.5 rounded text-xs transition-colors ${
                    gridSize === g ? 'bg-white text-[#1a5276] font-bold' : 'text-blue-200 hover:text-white'
                  }`}
                >
                  {g}mm
                </button>
              ))}
            </div>

            <button
              onClick={() => undo()}
              disabled={pastStates.length === 0}
              className="px-2 py-1 text-xs bg-white/10 hover:bg-white/20 rounded disabled:opacity-40 transition-colors"
              title="Ctrl+Z"
            >
              ↩{pastStates.length > 0 ? ` (${pastStates.length})` : ''}
            </button>
            <button
              onClick={() => redo()}
              disabled={futureStates.length === 0}
              className="px-2 py-1 text-xs bg-white/10 hover:bg-white/20 rounded disabled:opacity-40 transition-colors"
              title="Ctrl+Shift+Z"
            >
              {futureStates.length > 0 ? `(${futureStates.length}) ` : ''}↪
            </button>

            <button
              onClick={() => setShowModalPainel(true)}
              className="px-2.5 py-1 text-xs bg-white/15 hover:bg-white/25 text-white rounded transition-colors font-medium"
              title="Adicionar painel"
            >
              + Painel
            </button>

            <button
              onClick={() => setShowCatalogo(true)}
              className="px-2.5 py-1 text-xs bg-white/15 hover:bg-white/25 text-white rounded transition-colors font-medium"
              title="Catálogo de ferragens"
            >
              Ferragens
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleSalvar}
              disabled={saving}
              className="px-2.5 py-1.5 text-xs sm:text-sm bg-[#f59e0b] hover:bg-[#d97706] text-black font-semibold rounded transition-colors disabled:opacity-60"
            >
              {saving ? '...' : 'Salvar'}
            </button>
            {savedUrl && (
              <span className="text-xs text-green-300 hidden sm:inline max-w-xs truncate" title={savedUrl}>
                ✓ Salvo! URL copiada
              </span>
            )}
            <nav className="hidden md:flex gap-3 text-sm shrink-0">
              <Link href="/" className="text-blue-200 hover:text-white transition-colors">Tipologias</Link>
              <Link href="/importar" className="text-blue-200 hover:text-white transition-colors">Importar</Link>
              <Link href="/smart" className="text-blue-200 hover:text-white transition-colors">Smart Vision</Link>
            </nav>
          </div>
        </div>

        {/* Mobile toolbar row */}
        <div className="sm:hidden px-3 pb-2 flex items-center gap-2">
          <div className="flex items-center gap-1 text-xs text-blue-200">
            <span>Grid:</span>
            {GRID_OPTIONS.map((g) => (
              <button
                key={g}
                onClick={() => setGridSize(g)}
                className={`px-1.5 py-0.5 rounded text-xs ${gridSize === g ? 'bg-white text-[#1a5276] font-bold' : 'text-blue-200'}`}
              >
                {g}mm
              </button>
            ))}
          </div>
          <button onClick={() => undo()} disabled={pastStates.length === 0} className="px-2 py-0.5 text-xs bg-white/10 rounded disabled:opacity-40">↩</button>
          <button onClick={() => redo()} disabled={futureStates.length === 0} className="px-2 py-0.5 text-xs bg-white/10 rounded disabled:opacity-40">↪</button>
          <button onClick={() => setShowModalPainel(true)} className="px-2 py-0.5 text-xs bg-white/15 text-white rounded font-medium">+ Painel</button>
          <button onClick={() => setShowCatalogo(true)} className="px-2 py-0.5 text-xs bg-white/15 text-white rounded font-medium">Ferragens</button>
        </div>
      </header>

      {/* Main — stack vertically on mobile, side-by-side on md+ */}
      <main className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
        {/* Canvas area */}
        <div className="flex-1 p-3 flex flex-col min-h-0" style={{ minHeight: '300px' }}>
          <EditorCanvas />

          {/* Mobile: toggle properties button */}
          <div className="md:hidden mt-2 flex justify-center">
            <button
              onClick={() => setShowProps((v) => !v)}
              className="px-4 py-2 text-sm bg-[#1a5276] text-white rounded-full shadow transition-colors"
            >
              {showProps ? 'Fechar Propriedades' : `Propriedades${painelSelecionado ? ` — ${painelSelecionado.nome}` : ''}`}
            </button>
          </div>
        </div>

        {/* Properties panel — always visible md+, toggle on mobile */}
        <aside className={`
          md:w-80 md:flex md:flex-col md:shrink-0 md:border-l md:border-gray-200 bg-white overflow-y-auto
          ${showProps ? 'flex flex-col border-t border-gray-200 max-h-64 md:max-h-none' : 'hidden md:flex'}
        `}>
          <div className="p-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-800 text-sm">Propriedades</h2>
            <button onClick={() => setShowProps(false)} className="md:hidden text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
          </div>

          {painelSelecionado ? (
            <div className="p-4 flex flex-col gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">Painel</p>
                <p className="font-semibold text-gray-800">{painelSelecionado.nome}</p>
                <p className="text-xs text-gray-500">{painelSelecionado.classificacao}</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <PropField label="Largura (mm)" value={painelSelecionado.largura_mm}
                  onChange={(v) => atualizarPainel(painelSelecionado.nome, { largura_mm: Math.max(100, Math.min(6000, v)) })} />
                <PropField label="Altura (mm)" value={painelSelecionado.altura_mm}
                  onChange={(v) => atualizarPainel(painelSelecionado.nome, { altura_mm: Math.max(100, Math.min(6000, v)) })} />
                <PropField label="Pos X (mm)" value={painelSelecionado.posicao_x_mm ?? 0}
                  onChange={(v) => atualizarPainel(painelSelecionado.nome, { posicao_x_mm: v })} />
                <PropField label="Pos Y (mm)" value={painelSelecionado.posicao_y_mm ?? 0}
                  onChange={(v) => atualizarPainel(painelSelecionado.nome, { posicao_y_mm: v })} />
              </div>

              {painelSelecionado.ferragens.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-2 uppercase tracking-wide">Ferragens ({painelSelecionado.ferragens.length})</p>
                  <div className="flex flex-col gap-1">
                    {painelSelecionado.ferragens.map((f, i) => (
                      <div key={i} className="text-xs bg-gray-50 rounded p-2">
                        <span className="font-medium">{f.tipo}</span>
                        <span className="text-gray-500 ml-2">x:{f.x_mm}mm y:{f.y_mm}mm</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button onClick={() => setPainelSelecionado(null)} className="text-xs text-gray-500 hover:text-gray-700 underline self-start">
                Desselecionar
              </button>
            </div>
          ) : (
            <div className="p-4 text-sm text-gray-500">
              <p>Toque em um painel para editar suas propriedades.</p>
              <div className="mt-4">
                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Tipologia</p>
                <p className="font-medium text-gray-700">{tipologia.nome}</p>
                <p className="text-xs text-gray-500 mt-1">{tipologia.paineis.length} painel(is)</p>
              </div>
              <div className="mt-4">
                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Painéis</p>
                <div className="flex flex-col gap-1">
                  {tipologia.paineis.map((p) => (
                    <button key={p.nome} onClick={() => setPainelSelecionado(p.nome)}
                      className="text-left text-xs bg-gray-50 hover:bg-blue-50 rounded p-2 transition-colors">
                      <span className="font-medium">{p.nome}</span>
                      <span className="text-gray-500 ml-2">{p.largura_mm}×{p.altura_mm}mm</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </aside>
      </main>
    </div>
  )
}

interface PropFieldProps {
  label: string
  value: number
  onChange: (v: number) => void
}

function PropField({ label, value, onChange }: PropFieldProps) {
  return (
    <div>
      <label className="text-xs text-gray-500 block mb-1">{label}</label>
      <input
        type="number"
        value={value}
        onChange={(e) => {
          const v = parseFloat(e.target.value)
          if (!isNaN(v)) onChange(v)
        }}
        className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:border-blue-500"
      />
    </div>
  )
}

export default function EditorPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#F5F2EE] flex items-center justify-center text-gray-500">Carregando editor...</div>}>
      <EditorPageInner />
    </Suspense>
  )
}
