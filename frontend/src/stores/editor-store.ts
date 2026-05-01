'use client'

import { create } from 'zustand'
import { temporal } from 'zundo'

export interface FerragemPosicao {
  codigo: string
  fabricante_id?: string | null
  tipo: string
  x_mm: number
  y_mm: number
}

export interface Abertura {
  modo: 'abrir' | 'correr' | 'basculante' | 'maxim_ar' | 'pivotante'
  lado_dobradica?: 'esquerda' | 'direita' | 'topo' | 'base' | null
  angulo_max_graus?: number
}

export interface Painel {
  nome: string
  largura_mm: number
  altura_mm: number
  classificacao: 'movel' | 'fixo' | 'correr' | 'bandeira'
  ferragens: FerragemPosicao[]
  posicao_x_mm: number
  posicao_y_mm: number
  abertura?: Abertura | null
}

export interface OpcoesRender {
  cor: 'incolor' | 'verde' | 'fume' | 'bronze' | 'azul' | 'espelho'
  acabamento: 'cromado' | 'inox' | 'preto' | 'dourado'
  incluir_png: boolean
  incluir_pdf: boolean
  incluir_3d: boolean
}

export interface TipologiaEditor {
  nome: string
  categoria?: 'porta' | 'janela' | 'box' | 'outro' | null
  paineis: Painel[]
  opcoes: OpcoesRender
}

export const DEFAULT_TIPOLOGIA: TipologiaEditor = {
  nome: 'Porta de Abrir 900×2100',
  categoria: 'porta',
  paineis: [
    {
      nome: 'Painel',
      largura_mm: 900,
      altura_mm: 2100,
      classificacao: 'movel',
      ferragens: [],
      posicao_x_mm: 0,
      posicao_y_mm: 0,
    },
  ],
  opcoes: {
    cor: 'incolor',
    acabamento: 'cromado',
    incluir_png: true,
    incluir_pdf: false,
    incluir_3d: false,
  },
}

export type ModoEdicao = 'select' | 'drag' | 'resize'

interface EditorState {
  tipologia: TipologiaEditor
  painelSelecionadoNome: string | null
  ferragemSelecionada: { painelNome: string; idx: number } | null
  modoEdicao: ModoEdicao
  gridSize: number
}

interface EditorActions {
  setTipologia: (t: TipologiaEditor) => void
  setNome: (nome: string) => void
  setPainelSelecionado: (nome: string | null) => void
  setFerragemSelecionada: (fs: { painelNome: string; idx: number } | null) => void
  setModoEdicao: (modo: ModoEdicao) => void
  setGridSize: (size: number) => void
  atualizarPainel: (nome: string, updates: Partial<Omit<Painel, 'nome'>>) => void
  atualizarFerragem: (painelNome: string, idx: number, updates: Partial<FerragemPosicao>) => void
  adicionarPainel: (painel: Painel) => void
  removerPainel: (nome: string) => void
  adicionarFerragemAoPainel: (painelNome: string, ferragem: FerragemPosicao) => void
}

const initialState: EditorState = {
  tipologia: DEFAULT_TIPOLOGIA,
  painelSelecionadoNome: null,
  ferragemSelecionada: null,
  modoEdicao: 'select',
  gridSize: 10,
}

export const useEditorStore = create<EditorState & EditorActions>()(
  temporal(
    (set) => ({
      ...initialState,

      setTipologia: (t) => set({ tipologia: t }),

      setNome: (nome) =>
        set((s) => ({ tipologia: { ...s.tipologia, nome } })),

      setPainelSelecionado: (nome) =>
        set({ painelSelecionadoNome: nome, ferragemSelecionada: null }),

      setFerragemSelecionada: (fs) => set({ ferragemSelecionada: fs }),

      setModoEdicao: (modo) => set({ modoEdicao: modo }),

      setGridSize: (size) => set({ gridSize: size }),

      atualizarPainel: (nome, updates) =>
        set((s) => ({
          tipologia: {
            ...s.tipologia,
            paineis: s.tipologia.paineis.map((p) =>
              p.nome === nome ? { ...p, ...updates } : p
            ),
          },
        })),

      atualizarFerragem: (painelNome, idx, updates) =>
        set((s) => ({
          tipologia: {
            ...s.tipologia,
            paineis: s.tipologia.paineis.map((p) =>
              p.nome === painelNome
                ? {
                    ...p,
                    ferragens: p.ferragens.map((f, i) =>
                      i === idx ? { ...f, ...updates } : f
                    ),
                  }
                : p
            ),
          },
        })),

      adicionarPainel: (painel) =>
        set((s) => ({
          tipologia: {
            ...s.tipologia,
            paineis: [...s.tipologia.paineis, painel],
          },
        })),

      removerPainel: (nome) =>
        set((s) => ({
          tipologia: {
            ...s.tipologia,
            paineis: s.tipologia.paineis.filter((p) => p.nome !== nome),
          },
          painelSelecionadoNome:
            s.painelSelecionadoNome === nome ? null : s.painelSelecionadoNome,
        })),

      adicionarFerragemAoPainel: (painelNome, ferragem) =>
        set((s) => ({
          tipologia: {
            ...s.tipologia,
            paineis: s.tipologia.paineis.map((p) =>
              p.nome === painelNome
                ? { ...p, ferragens: [...p.ferragens, ferragem] }
                : p
            ),
          },
        })),
    }),
    { limit: 50 }
  )
)
