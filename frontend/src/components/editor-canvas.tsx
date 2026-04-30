'use client'

import { useRef, useCallback, useState } from 'react'
import {
  DndContext,
  PointerSensor,
  TouchSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import { useDraggable } from '@dnd-kit/core'
import { useEditorStore } from '@/stores/editor-store'
import type { Painel } from '@/stores/editor-store'

const CANVAS_PADDING = 100

export default function EditorCanvas() {
  const tipologia = useEditorStore((s) => s.tipologia)
  const painelSelecionadoNome = useEditorStore((s) => s.painelSelecionadoNome)
  const gridSize = useEditorStore((s) => s.gridSize)
  const setPainelSelecionado = useEditorStore((s) => s.setPainelSelecionado)
  const atualizarPainel = useEditorStore((s) => s.atualizarPainel)
  const svgRef = useRef<SVGSVGElement>(null)
  const [draggingId, setDraggingId] = useState<string | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 250, tolerance: 5 } }),
    useSensor(KeyboardSensor)
  )

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

  const svgPixelWidth = Math.min(canvasWidth, 800)
  const svgPixelHeight = Math.min(canvasHeight * (svgPixelWidth / canvasWidth), 600)

  const getSvgScale = useCallback(() => {
    if (!svgRef.current) return svgPixelWidth / canvasWidth
    const rect = svgRef.current.getBoundingClientRect()
    return rect.width / canvasWidth
  }, [svgPixelWidth, canvasWidth])

  const handleDragStart = useCallback((e: DragStartEvent) => {
    setDraggingId(String(e.active.id))
  }, [])

  const handleDragEnd = useCallback(
    (e: DragEndEvent) => {
      setDraggingId(null)
      const painelNome = String(e.active.id).replace(/^painel-/, '')
      const painel = tipologia.paineis.find((p) => p.nome === painelNome)
      if (!painel) return

      const scale = getSvgScale()
      const deltaX_mm = e.delta.x / scale
      const deltaY_mm = e.delta.y / scale

      const rawX = (painel.posicao_x_mm ?? 0) + deltaX_mm
      const rawY = (painel.posicao_y_mm ?? 0) + deltaY_mm

      const snappedX = Math.round(rawX / gridSize) * gridSize
      const snappedY = Math.round(rawY / gridSize) * gridSize

      atualizarPainel(painelNome, {
        posicao_x_mm: Math.max(0, snappedX),
        posicao_y_mm: Math.max(0, snappedY),
      })
    },
    [tipologia.paineis, getSvgScale, gridSize, atualizarPainel]
  )

  const hasOverlap = tipologia.paineis.some((a, i) =>
    tipologia.paineis.some((b, j) => {
      if (i >= j) return false
      const ax = a.posicao_x_mm ?? 0
      const ay = a.posicao_y_mm ?? 0
      const bx = b.posicao_x_mm ?? 0
      const by = b.posicao_y_mm ?? 0
      return (
        ax < bx + b.largura_mm &&
        ax + a.largura_mm > bx &&
        ay < by + b.altura_mm &&
        ay + a.altura_mm > by
      )
    })
  )

  return (
    <div className="flex-1 flex flex-col bg-gray-100 rounded-lg border border-gray-300 min-h-0 overflow-hidden">
      {hasOverlap && (
        <div className="shrink-0 bg-amber-50 border-b border-amber-200 text-amber-700 text-xs px-3 py-1.5">
          ⚠ Painéis sobrepostos — ajuste as posições
        </div>
      )}
      <div className="flex-1 overflow-auto">
        <div className="p-4 min-h-full flex items-start justify-center">
          <DndContext
            sensors={sensors}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <svg
              ref={svgRef}
              viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
              className="bg-white shadow-md"
              style={{
                width: svgPixelWidth,
                height: svgPixelHeight,
                cursor: 'default',
                touchAction: 'none',
              }}
              onClick={(e) => {
                if ((e.target as Element).tagName === 'svg') {
                  setPainelSelecionado(null)
                }
              }}
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

              <rect width={canvasWidth} height={canvasHeight} fill="#f9fafb" />
              <rect width={canvasWidth} height={canvasHeight} fill="url(#editor-grid)" />
              <rect width={canvasWidth} height={canvasHeight} fill="url(#editor-grid-major)" />

              <rect
                x={CANVAS_PADDING}
                y={CANVAS_PADDING}
                width={totalWidth}
                height={totalHeight}
                fill="white"
                stroke="#e5e7eb"
                strokeWidth="1"
              />

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

              {tipologia.paineis.map((painel) => (
                <DraggablePainel
                  key={painel.nome}
                  painel={painel}
                  selected={painelSelecionadoNome === painel.nome}
                  isDragging={draggingId === `painel-${painel.nome}`}
                  offsetX={CANVAS_PADDING}
                  offsetY={CANVAS_PADDING}
                  svgScale={svgPixelWidth / canvasWidth}
                  onSelect={() => setPainelSelecionado(painel.nome)}
                />
              ))}
            </svg>
          </DndContext>
        </div>
      </div>
    </div>
  )
}

interface DraggablePainelProps {
  painel: Painel
  selected: boolean
  isDragging: boolean
  offsetX: number
  offsetY: number
  svgScale: number
  onSelect: () => void
}

function DraggablePainel({
  painel,
  selected,
  isDragging,
  offsetX,
  offsetY,
  svgScale,
  onSelect,
}: DraggablePainelProps) {
  const { setNodeRef, listeners, attributes, transform } = useDraggable({
    id: `painel-${painel.nome}`,
  })

  const baseX = offsetX + (painel.posicao_x_mm ?? 0)
  const baseY = offsetY + (painel.posicao_y_mm ?? 0)

  const dragOffsetX = transform ? transform.x / svgScale : 0
  const dragOffsetY = transform ? transform.y / svgScale : 0
  const x = baseX + dragOffsetX
  const y = baseY + dragOffsetY

  return (
    <>
      {/* Ghost at origin while dragging */}
      {isDragging && (
        <rect
          x={baseX}
          y={baseY}
          width={painel.largura_mm}
          height={painel.altura_mm}
          fill="none"
          stroke="#9ca3af"
          strokeWidth="1"
          strokeDasharray="6 3"
          style={{ pointerEvents: 'none' }}
        />
      )}

      <g
        ref={(el) => setNodeRef(el as unknown as HTMLElement)}
        {...listeners}
        {...attributes}
        onClick={(e) => { e.stopPropagation(); onSelect() }}
        style={{ cursor: isDragging ? 'grabbing' : 'grab', touchAction: 'none' }}
      >
        <rect
          x={x}
          y={y}
          width={painel.largura_mm}
          height={painel.altura_mm}
          fill={selected ? '#dbeafe' : isDragging ? '#eff6ff' : '#e8f4fd'}
          stroke={selected ? '#3b82f6' : isDragging ? '#60a5fa' : '#1a5276'}
          strokeWidth={selected || isDragging ? 2 : 1}
          style={{ pointerEvents: 'all' }}
        />

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
          {isDragging
            ? `${Math.round((painel.posicao_x_mm ?? 0) + dragOffsetX)}×${Math.round((painel.posicao_y_mm ?? 0) + dragOffsetY)}mm`
            : `${painel.largura_mm}×${painel.altura_mm}mm`}
        </text>

        {painel.ferragens.map((f, i) => (
          <circle
            key={i}
            cx={x + f.x_mm}
            cy={y + f.y_mm}
            r={6}
            fill="#f59e0b"
            stroke="#92400e"
            strokeWidth="1"
          />
        ))}

        {selected && !isDragging && (
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
    </>
  )
}
