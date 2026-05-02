'use client'

import { useState, useEffect, useCallback } from 'react'
import type { Painel } from '@/stores/editor-store'

type Classificacao = Painel['classificacao']

interface TipoConfig {
  label: string
  largura_mm: number
  altura_mm: number
  descricao: string
  nomeBase: string
}

const TIPOS: Record<Classificacao, TipoConfig> = {
  movel: { label: 'Móvel',    largura_mm: 900, altura_mm: 2100, descricao: 'Folha de abrir / giratória', nomeBase: 'Painel Móvel' },
  fixo:  { label: 'Fixo',     largura_mm: 600, altura_mm: 2100, descricao: 'Vidro fixo lateral',         nomeBase: 'Painel Fixo' },
  correr:{ label: 'Correr',   largura_mm: 800, altura_mm: 2100, descricao: 'Folha deslizante',           nomeBase: 'Painel Correr' },
  bandeira:{ label:'Bandeira',largura_mm: 900, altura_mm:  400, descricao: 'Bandeira / travessa',        nomeBase: 'Painel Bandeira' },
}

function gerarNomeUnico(base: string, existentes: Set<string>): string {
  if (!existentes.has(base)) return base
  for (let i = 2; i < 100; i++) {
    const nome = `${base} ${i}`
    if (!existentes.has(nome)) return nome
  }
  return `${base} ${Date.now()}`
}

interface Props {
  nomesExistentes: string[]
  proximaPosicaoX: number
  onConfirmar: (painel: Painel) => void
  onCancelar: () => void
}

export default function ModalAdicionarPainel({
  nomesExistentes,
  proximaPosicaoX,
  onConfirmar,
  onCancelar,
}: Props) {
  const [tipo, setTipo] = useState<Classificacao>('movel')
  const [largura, setLargura] = useState(TIPOS.movel.largura_mm)
  const [altura, setAltura] = useState(TIPOS.movel.altura_mm)
  const [nome, setNome] = useState(() =>
    gerarNomeUnico(TIPOS.movel.nomeBase, new Set(nomesExistentes))
  )

  const existentesSet = new Set(nomesExistentes)

  const selectTipo = useCallback((t: Classificacao) => {
    setTipo(t)
    setLargura(TIPOS[t].largura_mm)
    setAltura(TIPOS[t].altura_mm)
    setNome(gerarNomeUnico(TIPOS[t].nomeBase, existentesSet))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nomesExistentes])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancelar()
      if (e.key === 'Enter') handleConfirmar()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nome, largura, altura, tipo])

  function handleConfirmar() {
    const nomeFinal = nome.trim() || gerarNomeUnico(TIPOS[tipo].nomeBase, existentesSet)
    onConfirmar({
      nome: nomeFinal,
      largura_mm: Math.max(100, Math.min(6000, largura)),
      altura_mm: Math.max(100, Math.min(6000, altura)),
      classificacao: tipo,
      ferragens: [],
      posicao_x_mm: proximaPosicaoX,
      posicao_y_mm: 0,
    })
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={(e) => { if (e.target === e.currentTarget) onCancelar() }}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        <div className="bg-[#1a5276] text-white px-5 py-3 flex items-center justify-between">
          <h2 className="font-semibold text-base">Adicionar Painel</h2>
          <button onClick={onCancelar} className="text-blue-200 hover:text-white text-xl leading-none">×</button>
        </div>

        <div className="p-5 flex flex-col gap-4">
          {/* Tipo selector */}
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Tipo</p>
            <div className="grid grid-cols-2 gap-2">
              {(Object.entries(TIPOS) as [Classificacao, TipoConfig][]).map(([key, cfg]) => (
                <button
                  key={key}
                  onClick={() => selectTipo(key)}
                  className={`text-left rounded-lg border-2 p-3 transition-colors ${
                    tipo === key
                      ? 'border-[#1a5276] bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <p className="font-semibold text-sm text-gray-800">{cfg.label}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{cfg.descricao}</p>
                  <p className="text-xs text-gray-400 mt-1">{cfg.largura_mm}×{cfg.altura_mm}mm</p>
                </button>
              ))}
            </div>
          </div>

          {/* Name */}
          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wide block mb-1">Nome</label>
            <input
              type="text"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              maxLength={100}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:border-[#1a5276]"
              autoFocus
            />
          </div>

          {/* Dimensions */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Largura (mm)</label>
              <input
                type="number"
                value={largura}
                min={100} max={6000}
                onChange={(e) => setLargura(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:border-[#1a5276]"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Altura (mm)</label>
              <input
                type="number"
                value={altura}
                min={100} max={6000}
                onChange={(e) => setAltura(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:border-[#1a5276]"
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 justify-end pt-1">
            <button
              onClick={onCancelar}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={handleConfirmar}
              disabled={!nome.trim()}
              className="px-4 py-2 text-sm bg-[#1a5276] hover:bg-[#154360] text-white font-semibold rounded-lg transition-colors disabled:opacity-50"
            >
              Adicionar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
