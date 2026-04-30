'use client'

import { useRef, useCallback } from 'react'
import { useEditorStore } from '@/stores/editor-store'
import type { Painel } from '@/stores/editor-store'

const CANVAS_PADDING = 100

export default function EditorCanvas() {
  const tipologia = useEditorStore((s) => s.tipologia)
  const painelSelecionadoNome = useEditorStore((s) => s.painelSelecionadoNome)
  const gridSize = useEditorStore((s) => s.gridSize)
  const setPainelSelecionado = useEditorStore((s) => s.setPainelSelecionado)
  const svgRef = useRef<SVGSVGElement>(null)

  const totalWidth = Math.max(
    ...tipologia.paineis.map((p) => (p.posicao_x_mm ?? 0) + p.largura_mm),
    100
  )
  const totalHeight = Math.max(
    ...tipologia.paineis.map((p) => (p.posicao_y_mm ?? 0) + p.altura_mm),
    100
  )

  const canvasWidth = totalWidth + CANVAS_PADDING * 2
  const canvasHeight = totalHeight + CANVAS_PADDING * 2

  const handleSvgClick = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (e.target === svgRef.current || (e.target as Element).tagName === 'rect') {
        const tag = (e.target as Element).tagName
        if (tag !== 'rect') {
          setPainelSelecionado(null)
        }
      }
    },
    [setPainelSelecionado]
  )

  return (
    <div className="flex-1 bg-gray-100 overflow-auto rounded-lg border border-gray-300 min-h-0">
      <div className="p-4 min-h-full flex items-start justify-center">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
          className="bg-white shadow-md"
          style={{
            width: Math.min(canvasWidth, 800),
            height: Math.min(canvasHeight * (Math.min(canvasWidth, 800) / canvasWidth), 600),
            cursor: 'default',
          }}
          onClick={handleSvgClick}
        >
          <defs>
            <pattern
              id="editor-grid"
              width={gridSize}
              height={gridSize}
              patternUnits="userSpaceOnUse"
              x={CANVAS_PADDING}
              y={CANVAS_PADDING}
            >
              <path
                d={`M ${gridSize} 0 L 0 0 0 ${gridSize}`}
                fill="none"
                stroke="#d1d5db"
                strokeWidth="0.3"
              />
            </pattern>
            <pattern
              id="editor-grid-major"
              width={gridSize * 10}
              height={gridSize * 10}
              patternUnits="userSpaceOnUse"
              x={CANVAS_PADDING}
              y={CANVAS_PADDING}
            >
              <path
                d={`M ${gridSize * 10} 0 L 0 0 0 ${gridSize * 10}`}
                fill="none"
                stroke="#9ca3af"
                strokeWidth="0.5"
              />
            </pattern>
          </defs>

          {/* Grid background */}
          <rect width={canvasWidth} height={canvasHeight} fill="#f9fafb" />
          <rect width={canvasWidth} height={canvasHeight} fill="url(#editor-grid)" />
          <rect width={canvasWidth} height={canvasHeight} fill="url(#editor-grid-major)" />

          {/* Canvas area boundary */}
          <rect
            x={CANVAS_PADDING}
            y={CANVAS_PADDING}
            width={totalWidth}
            height={totalHeight}
            fill="white"
            stroke="#e5e7eb"
            strokeWidth="1"
          />

          {/* Dimension labels */}
          <text
            x={CANVAS_PADDING + totalWidth / 2}
            y={CANVAS_PADDING - 10}
            textAnchor="middle"
            fontSize="8"
            fill="#6b7280"
          >
            {totalWidth}mm
          </text>
          <text
            x={CANVAS_PADDING - 10}
            y={CANVAS_PADDING + totalHeight / 2}
            textAnchor="middle"
            fontSize="8"
            fill="#6b7280"
            transform={`rotate(-90, ${CANVAS_PADDING - 10}, ${CANVAS_PADDING + totalHeight / 2})`}
          >
            {totalHeight}mm
          </text>

          {/* Painéis */}
          {tipologia.paineis.map((painel) => (
            <PainelSvg
              key={painel.nome}
              painel={painel}
              selected={painelSelecionadoNome === painel.nome}
              offsetX={CANVAS_PADDING}
              offsetY={CANVAS_PADDING}
              onSelect={() => setPainelSelecionado(painel.nome)}
            />
          ))}
        </svg>
      </div>
    </div>
  )
}

interface PainelSvgProps {
  painel: Painel
  selected: boolean
  offsetX: number
  offsetY: number
  onSelect: () => void
}

function PainelSvg({ painel, selected, offsetX, offsetY, onSelect }: PainelSvgProps) {
  const x = offsetX + (painel.posicao_x_mm ?? 0)
  const y = offsetY + (painel.posicao_y_mm ?? 0)

  return (
    <g onClick={(e) => { e.stopPropagation(); onSelect() }}>
      <rect
        x={x}
        y={y}
        width={painel.largura_mm}
        height={painel.altura_mm}
        fill={selected ? '#dbeafe' : '#e8f4fd'}
        stroke={selected ? '#3b82f6' : '#1a5276'}
        strokeWidth={selected ? 2 : 1}
        style={{ cursor: 'pointer' }}
      />

      {/* Label */}
      <text
        x={x + painel.largura_mm / 2}
        y={y + painel.altura_mm / 2 - 8}
        textAnchor="middle"
        fontSize="10"
        fill={selected ? '#1d4ed8' : '#1a5276'}
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {painel.nome}
      </text>
      <text
        x={x + painel.largura_mm / 2}
        y={y + painel.altura_mm / 2 + 6}
        textAnchor="middle"
        fontSize="8"
        fill={selected ? '#3b82f6' : '#374151'}
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {painel.largura_mm}×{painel.altura_mm}mm
      </text>

      {/* Ferragens */}
      {painel.ferragens.map((f, i) => (
        <circle
          key={i}
          cx={x + f.x_mm}
          cy={y + f.y_mm}
          r={6}
          fill="#f59e0b"
          stroke="#92400e"
          strokeWidth="1"
          style={{ cursor: 'pointer' }}
        />
      ))}

      {/* Selection outline */}
      {selected && (
        <rect
          x={x - 2}
          y={y - 2}
          width={painel.largura_mm + 4}
          height={painel.altura_mm + 4}
          fill="none"
          stroke="#3b82f6"
          strokeWidth="1"
          strokeDasharray="4 2"
          style={{ pointerEvents: 'none' }}
        />
      )}
    </g>
  )
}
