'use client'

import { useRef, useCallback, useState, useReducer, useEffect } from 'react'
import {
  DndContext,
  PointerSensor,
  TouchSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  useDraggable,
  type DragEndEvent,
  type DragStartEvent,
  type DragMoveEvent,
} from '@dnd-kit/core'
import { useEditorStore } from '@/stores/editor-store'
import type { Painel, FerragemPosicao } from '@/stores/editor-store'

const CANVAS_PADDING = 100
const HANDLE_SIZE = 16
type Corner = 'nw' | 'ne' | 'sw' | 'se'

// ── Recorte cache (module-level — persiste entre re-renders) ──────────────────

interface CanonicalRecorte {
  categoria: string | null
  recorte_largura_mm: number | null
  recorte_altura_mm: number | null
}

const _recorteCache: Record<string, CanonicalRecorte | null> = {}
const _fetchingSet = new Set<string>()

// ── Cores por categoria ───────────────────────────────────────────────────────

const CATEGORIA_COR: Record<string, { fill: string; stroke: string; fillDrag: string }> = {
  dobradica:        { fill: '#3b82f6', stroke: '#1e40af', fillDrag: '#60a5fa' },
  fechadura:        { fill: '#ef4444', stroke: '#991b1b', fillDrag: '#f87171' },
  bico_papagaio:    { fill: '#ef4444', stroke: '#991b1b', fillDrag: '#f87171' },
  suporte:          { fill: '#22c55e', stroke: '#166534', fillDrag: '#4ade80' },
  trinco:           { fill: '#f97316', stroke: '#9a3412', fillDrag: '#fb923c' },
  puxador:          { fill: '#a855f7', stroke: '#6b21a8', fillDrag: '#c084fc' },
  contra_fechadura: { fill: '#f97316', stroke: '#9a3412', fillDrag: '#fb923c' },
  batedor:          { fill: '#22c55e', stroke: '#166534', fillDrag: '#4ade80' },
}
const COR_DEFAULT = { fill: '#f59e0b', stroke: '#92400e', fillDrag: '#fbbf24' }

function getCategoriaCor(categoria: string | null | undefined) {
  return (categoria && CATEGORIA_COR[categoria]) || COR_DEFAULT
}

interface ResizingStart {
  painelNome: string
  handle: Corner
  startW: number
  startH: number
  startX: number
  startY: number
}

interface ResizePreview {
  painelNome: string
  largura_mm: number
  altura_mm: number
  posicao_x_mm: number
  posicao_y_mm: number
}

export default function EditorCanvas() {
  const tipologia = useEditorStore((s) => s.tipologia)
  const painelSelecionadoNome = useEditorStore((s) => s.painelSelecionadoNome)
  const gridSize = useEditorStore((s) => s.gridSize)
  const setPainelSelecionado = useEditorStore((s) => s.setPainelSelecionado)
  const ferragemSelecionada = useEditorStore((s) => s.ferragemSelecionada)
  const setFerragemSelecionada = useEditorStore((s) => s.setFerragemSelecionada)
  const atualizarPainel = useEditorStore((s) => s.atualizarPainel)
  const atualizarFerragem = useEditorStore((s) => s.atualizarFerragem)
  const adicionarFerragemAoPainel = useEditorStore((s) => s.adicionarFerragemAoPainel)
  const svgRef = useRef<SVGSVGElement>(null)
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [resizePreview, setResizePreview] = useState<ResizePreview | null>(null)
  const resizingStartRef = useRef<ResizingStart | null>(null)
  const [catalogDropTarget, setCatalogDropTarget] = useState<string | null>(null)
  const [, forceUpdate] = useReducer((v: number) => v + 1, 0)

  useEffect(() => {
    const codes = new Set(tipologia.paineis.flatMap((p) => p.ferragens.map((f) => f.codigo)))
    codes.forEach((codigo) => {
      if (codigo in _recorteCache || _fetchingSet.has(codigo)) return
      _fetchingSet.add(codigo)
      fetch(`/api/v2/ferragens/${encodeURIComponent(codigo)}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          _recorteCache[codigo] = data
            ? { categoria: data.categoria ?? null, recorte_largura_mm: data.recorte_largura_mm ?? null, recorte_altura_mm: data.recorte_altura_mm ?? null }
            : null
          forceUpdate()
        })
        .catch(() => { _recorteCache[codigo] = null })
        .finally(() => _fetchingSet.delete(codigo))
    })
  }, [tipologia.paineis])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 250, tolerance: 5 } }),
    useSensor(KeyboardSensor)
  )

  const totalWidth = Math.max(
    ...tipologia.paineis.map((p) => (resizePreview?.painelNome === p.nome ? resizePreview.posicao_x_mm + resizePreview.largura_mm : (p.posicao_x_mm ?? 0) + p.largura_mm)),
    100
  )
  const totalHeight = Math.max(
    ...tipologia.paineis.map((p) => (resizePreview?.painelNome === p.nome ? resizePreview.posicao_y_mm + resizePreview.altura_mm : (p.posicao_y_mm ?? 0) + p.altura_mm)),
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

  const snapVal = useCallback((v: number) => Math.round(v / gridSize) * gridSize, [gridSize])

  const clientToMm = useCallback(
    (clientX: number, clientY: number) => {
      if (!svgRef.current) return null
      const rect = svgRef.current.getBoundingClientRect()
      const scaleX = canvasWidth / rect.width
      const scaleY = canvasHeight / rect.height
      return {
        mmX: (clientX - rect.left) * scaleX - CANVAS_PADDING,
        mmY: (clientY - rect.top) * scaleY - CANVAS_PADDING,
      }
    },
    [canvasWidth, canvasHeight]
  )

  const findPainelAt = useCallback(
    (mmX: number, mmY: number) =>
      tipologia.paineis.find((p) => {
        const px = p.posicao_x_mm ?? 0
        const py = p.posicao_y_mm ?? 0
        return mmX >= px && mmX <= px + p.largura_mm && mmY >= py && mmY <= py + p.altura_mm
      }) ?? null,
    [tipologia.paineis]
  )

  const handleCatalogDragOver = useCallback(
    (e: React.DragEvent<SVGSVGElement>) => {
      if (!e.dataTransfer.types.includes('application/vnd.vdx.canonical')) return
      e.preventDefault()
      e.dataTransfer.dropEffect = 'copy'
      const pos = clientToMm(e.clientX, e.clientY)
      if (!pos) return
      const painel = findPainelAt(pos.mmX, pos.mmY)
      setCatalogDropTarget(painel?.nome ?? null)
    },
    [clientToMm, findPainelAt]
  )

  const handleCatalogDragLeave = useCallback((e: React.DragEvent<SVGSVGElement>) => {
    if ((e.currentTarget as Element).contains(e.relatedTarget as Node)) return
    setCatalogDropTarget(null)
  }, [])

  const handleCatalogDrop = useCallback(
    (e: React.DragEvent<SVGSVGElement>) => {
      e.preventDefault()
      setCatalogDropTarget(null)
      const raw = e.dataTransfer.getData('application/vnd.vdx.canonical')
      if (!raw) return
      let canonical: { canonical_id: string; categoria: string | null; nome_apresentacao: string }
      try { canonical = JSON.parse(raw) } catch { return }
      if (!canonical.canonical_id) return

      const pos = clientToMm(e.clientX, e.clientY)
      if (!pos) return
      const painel = findPainelAt(pos.mmX, pos.mmY)
      if (!painel) return

      const localX = pos.mmX - (painel.posicao_x_mm ?? 0)
      const localY = pos.mmY - (painel.posicao_y_mm ?? 0)
      adicionarFerragemAoPainel(painel.nome, {
        codigo: canonical.canonical_id,
        fabricante_id: null,
        tipo: canonical.categoria ?? canonical.nome_apresentacao,
        x_mm: Math.max(0, Math.min(painel.largura_mm, snapVal(localX))),
        y_mm: Math.max(0, Math.min(painel.altura_mm, snapVal(localY))),
      })
      setPainelSelecionado(painel.nome)
    },
    [clientToMm, findPainelAt, snapVal, adicionarFerragemAoPainel, setPainelSelecionado]
  )

  const handleDragStart = useCallback(
    (e: DragStartEvent) => {
      const id = String(e.active.id)
      setDraggingId(id)
      if (id.startsWith('resize-')) {
        const parts = id.slice('resize-'.length).split('-')
        const handle = parts.pop() as Corner
        const painelNome = parts.join('-')
        const painel = tipologia.paineis.find((p) => p.nome === painelNome)
        if (painel) {
          resizingStartRef.current = {
            painelNome,
            handle,
            startW: painel.largura_mm,
            startH: painel.altura_mm,
            startX: painel.posicao_x_mm ?? 0,
            startY: painel.posicao_y_mm ?? 0,
          }
        }
      }
    },
    [tipologia.paineis]
  )

  const handleDragMove = useCallback(
    (e: DragMoveEvent) => {
      const id = String(e.active.id)
      if (!id.startsWith('resize-')) return
      const start = resizingStartRef.current
      if (!start) return

      const scale = getSvgScale()
      const dx = e.delta.x / scale
      const dy = e.delta.y / scale
      const { startW, startH, startX, startY, handle } = start

      let newW = startW
      let newH = startH
      let newX = startX
      let newY = startY

      switch (handle) {
        case 'se':
          newW = Math.max(100, Math.min(6000, snapVal(startW + dx)))
          newH = Math.max(100, Math.min(6000, snapVal(startH + dy)))
          break
        case 'ne':
          newW = Math.max(100, Math.min(6000, snapVal(startW + dx)))
          newH = Math.max(100, Math.min(6000, snapVal(startH - dy)))
          newY = snapVal(startY + dy)
          break
        case 'sw':
          newW = Math.max(100, Math.min(6000, snapVal(startW - dx)))
          newX = snapVal(startX + dx)
          newH = Math.max(100, Math.min(6000, snapVal(startH + dy)))
          break
        case 'nw':
          newW = Math.max(100, Math.min(6000, snapVal(startW - dx)))
          newX = snapVal(startX + dx)
          newH = Math.max(100, Math.min(6000, snapVal(startH - dy)))
          newY = snapVal(startY + dy)
          break
      }

      setResizePreview({
        painelNome: start.painelNome,
        largura_mm: newW,
        altura_mm: newH,
        posicao_x_mm: newX,
        posicao_y_mm: newY,
      })
    },
    [getSvgScale, snapVal]
  )

  const handleDragEnd = useCallback(
    (e: DragEndEvent) => {
      const id = String(e.active.id)
      setDraggingId(null)

      if (id.startsWith('resize-')) {
        resizingStartRef.current = null
        if (resizePreview) {
          atualizarPainel(resizePreview.painelNome, {
            largura_mm: resizePreview.largura_mm,
            altura_mm: resizePreview.altura_mm,
            posicao_x_mm: resizePreview.posicao_x_mm,
            posicao_y_mm: resizePreview.posicao_y_mm,
          })
          setResizePreview(null)
        }
        return
      }

      const scale = getSvgScale()

      if (id.startsWith('painel-')) {
        const painelNome = id.slice('painel-'.length)
        const painel = tipologia.paineis.find((p) => p.nome === painelNome)
        if (!painel) return
        const snappedX = Math.max(0, snapVal((painel.posicao_x_mm ?? 0) + e.delta.x / scale))
        const snappedY = Math.max(0, snapVal((painel.posicao_y_mm ?? 0) + e.delta.y / scale))
        atualizarPainel(painelNome, { posicao_x_mm: snappedX, posicao_y_mm: snappedY })
      } else if (id.startsWith('ferragem-')) {
        const parts = id.slice('ferragem-'.length).split('-')
        const idx = parseInt(parts.pop()!, 10)
        const painelNome = parts.join('-')
        const painel = tipologia.paineis.find((p) => p.nome === painelNome)
        if (!painel || isNaN(idx)) return
        const ferragem = painel.ferragens[idx]
        if (!ferragem) return
        const rawX = ferragem.x_mm + e.delta.x / scale
        const rawY = ferragem.y_mm + e.delta.y / scale
        atualizarFerragem(painelNome, idx, {
          x_mm: Math.max(0, Math.min(painel.largura_mm, snapVal(rawX))),
          y_mm: Math.max(0, Math.min(painel.altura_mm, snapVal(rawY))),
        })
      }
    },
    [tipologia.paineis, getSvgScale, snapVal, atualizarPainel, atualizarFerragem, resizePreview]
  )

  const hasOverlap = tipologia.paineis.some((a, i) =>
    tipologia.paineis.some((b, j) => {
      if (i >= j) return false
      const ax = a.posicao_x_mm ?? 0; const ay = a.posicao_y_mm ?? 0
      const bx = b.posicao_x_mm ?? 0; const by = b.posicao_y_mm ?? 0
      return ax < bx + b.largura_mm && ax + a.largura_mm > bx && ay < by + b.altura_mm && ay + a.altura_mm > by
    })
  )

  const draggingFerragemPainelNome = draggingId?.startsWith('ferragem-')
    ? draggingId.slice('ferragem-'.length).split('-').slice(0, -1).join('-')
    : null

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
            onDragMove={handleDragMove}
            onDragEnd={handleDragEnd}
          >
            <svg
              ref={svgRef}
              viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
              className="bg-white shadow-md"
              style={{ width: svgPixelWidth, height: svgPixelHeight, cursor: 'default', touchAction: 'none' }}
              onClick={(e) => {
                if ((e.target as Element).tagName === 'svg') setPainelSelecionado(null)
              }}
              onDragOver={handleCatalogDragOver}
              onDragLeave={handleCatalogDragLeave}
              onDrop={handleCatalogDrop}
            >
              <defs>
                <pattern id="editor-grid" width={gridSize} height={gridSize} patternUnits="userSpaceOnUse" x={CANVAS_PADDING} y={CANVAS_PADDING}>
                  <path d={`M ${gridSize} 0 L 0 0 0 ${gridSize}`} fill="none" stroke="#d1d5db" strokeWidth="0.3" />
                </pattern>
                <pattern id="editor-grid-major" width={gridSize * 10} height={gridSize * 10} patternUnits="userSpaceOnUse" x={CANVAS_PADDING} y={CANVAS_PADDING}>
                  <path d={`M ${gridSize * 10} 0 L 0 0 0 ${gridSize * 10}`} fill="none" stroke="#9ca3af" strokeWidth="0.5" />
                </pattern>
              </defs>

              <rect width={canvasWidth} height={canvasHeight} fill="#f9fafb" />
              <rect width={canvasWidth} height={canvasHeight} fill="url(#editor-grid)" />
              <rect width={canvasWidth} height={canvasHeight} fill="url(#editor-grid-major)" />
              <rect x={CANVAS_PADDING} y={CANVAS_PADDING} width={totalWidth} height={totalHeight} fill="white" stroke="#e5e7eb" strokeWidth="1" />

              <text x={CANVAS_PADDING + totalWidth / 2} y={CANVAS_PADDING - 10} textAnchor="middle" fontSize="8" fill="#6b7280">{totalWidth}mm</text>
              <text x={CANVAS_PADDING - 10} y={CANVAS_PADDING + totalHeight / 2} textAnchor="middle" fontSize="8" fill="#6b7280" transform={`rotate(-90, ${CANVAS_PADDING - 10}, ${CANVAS_PADDING + totalHeight / 2})`}>{totalHeight}mm</text>

              {tipologia.paineis.map((painel) => {
                const preview = resizePreview?.painelNome === painel.nome ? resizePreview : null
                const displayPainel = preview
                  ? { ...painel, largura_mm: preview.largura_mm, altura_mm: preview.altura_mm, posicao_x_mm: preview.posicao_x_mm, posicao_y_mm: preview.posicao_y_mm }
                  : painel
                return (
                  <DraggablePainel
                    key={painel.nome}
                    painel={displayPainel}
                    selected={painelSelecionadoNome === painel.nome}
                    isPainelDragging={draggingId === `painel-${painel.nome}`}
                    isResizing={draggingId?.startsWith(`resize-${painel.nome}`) ?? false}
                    isFerragemDragParent={draggingFerragemPainelNome === painel.nome}
                    isCatalogDropTarget={catalogDropTarget === painel.nome}
                    recorteCache={_recorteCache}
                    ferragemSelecionadaIdx={
                      ferragemSelecionada?.painelNome === painel.nome
                        ? ferragemSelecionada.idx
                        : null
                    }
                    onSelectFerragem={(idx) => setFerragemSelecionada({ painelNome: painel.nome, idx })}
                    offsetX={CANVAS_PADDING}
                    offsetY={CANVAS_PADDING}
                    svgScale={svgPixelWidth / canvasWidth}
                    onSelect={() => setPainelSelecionado(painel.nome)}
                  />
                )
              })}
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
  isPainelDragging: boolean
  isResizing: boolean
  isFerragemDragParent: boolean
  isCatalogDropTarget: boolean
  recorteCache: Record<string, CanonicalRecorte | null>
  ferragemSelecionadaIdx: number | null
  onSelectFerragem: (idx: number) => void
  offsetX: number
  offsetY: number
  svgScale: number
  onSelect: () => void
}

function DraggablePainel({ painel, selected, isPainelDragging, isResizing, isFerragemDragParent, isCatalogDropTarget, recorteCache, ferragemSelecionadaIdx, onSelectFerragem, offsetX, offsetY, svgScale, onSelect }: DraggablePainelProps) {
  const { setNodeRef, listeners, attributes, transform } = useDraggable({
    id: `painel-${painel.nome}`,
    disabled: isResizing,
  })

  const baseX = offsetX + (painel.posicao_x_mm ?? 0)
  const baseY = offsetY + (painel.posicao_y_mm ?? 0)

  const dragOffsetX = transform && !isResizing ? transform.x / svgScale : 0
  const dragOffsetY = transform && !isResizing ? transform.y / svgScale : 0
  const x = baseX + dragOffsetX
  const y = baseY + dragOffsetY

  return (
    <>
      {isPainelDragging && (
        <rect x={baseX} y={baseY} width={painel.largura_mm} height={painel.altura_mm} fill="none" stroke="#9ca3af" strokeWidth="1" strokeDasharray="6 3" style={{ pointerEvents: 'none' }} />
      )}

      <g
        ref={(el) => setNodeRef(el as unknown as HTMLElement)}
        {...(isResizing ? {} : listeners)}
        {...(isResizing ? {} : attributes)}
        onClick={(e) => { e.stopPropagation(); onSelect() }}
        style={{ cursor: isPainelDragging ? 'grabbing' : isResizing ? 'default' : 'grab', touchAction: 'none' }}
      >
        <rect
          x={x} y={y}
          width={painel.largura_mm} height={painel.altura_mm}
          fill={
            isCatalogDropTarget ? '#dcfce7' :
            selected || isResizing ? '#dbeafe' :
            isPainelDragging || isFerragemDragParent ? '#eff6ff' : '#e8f4fd'
          }
          stroke={
            isCatalogDropTarget ? '#16a34a' :
            selected || isResizing ? '#3b82f6' :
            isPainelDragging ? '#60a5fa' :
            isFerragemDragParent ? '#93c5fd' : '#1a5276'
          }
          strokeWidth={isCatalogDropTarget || selected || isPainelDragging || isResizing || isFerragemDragParent ? 2 : 1}
          strokeDasharray={isCatalogDropTarget ? '6 3' : undefined}
          style={{ pointerEvents: 'all' }}
        />

        <text x={x + painel.largura_mm / 2} y={y + painel.altura_mm / 2 - 8} textAnchor="middle" fontSize="10" fill={selected ? '#1d4ed8' : '#1a5276'} style={{ pointerEvents: 'none', userSelect: 'none' }}>
          {painel.nome}
        </text>
        <text x={x + painel.largura_mm / 2} y={y + painel.altura_mm / 2 + 6} textAnchor="middle" fontSize="8" fill={selected ? '#3b82f6' : '#374151'} style={{ pointerEvents: 'none', userSelect: 'none' }}>
          {isPainelDragging
            ? `${Math.round((painel.posicao_x_mm ?? 0) + dragOffsetX)},${Math.round((painel.posicao_y_mm ?? 0) + dragOffsetY)}mm`
            : isResizing
            ? `${painel.largura_mm}×${painel.altura_mm}mm`
            : `${painel.largura_mm}×${painel.altura_mm}mm`}
        </text>

        {painel.ferragens.map((f, i) => (
          <DraggableFerragem
            key={i}
            ferragem={f}
            idx={i}
            painelNome={painel.nome}
            painelX={x}
            painelY={y}
            svgScale={svgScale}
            recorte={recorteCache[f.codigo] ?? null}
            isSelected={ferragemSelecionadaIdx === i}
            onSelect={() => onSelectFerragem(i)}
          />
        ))}

        {selected && !isPainelDragging && (
          <rect x={x - 2} y={y - 2} width={painel.largura_mm + 4} height={painel.altura_mm + 4} fill="none" stroke="#3b82f6" strokeWidth="1" strokeDasharray="4 2" style={{ pointerEvents: 'none' }} />
        )}

        {/* Resize handles — shown when selected */}
        {selected && (
          <>
            <ResizeHandle painelNome={painel.nome} corner="nw" x={x - HANDLE_SIZE / 2} y={y - HANDLE_SIZE / 2} />
            <ResizeHandle painelNome={painel.nome} corner="ne" x={x + painel.largura_mm - HANDLE_SIZE / 2} y={y - HANDLE_SIZE / 2} />
            <ResizeHandle painelNome={painel.nome} corner="sw" x={x - HANDLE_SIZE / 2} y={y + painel.altura_mm - HANDLE_SIZE / 2} />
            <ResizeHandle painelNome={painel.nome} corner="se" x={x + painel.largura_mm - HANDLE_SIZE / 2} y={y + painel.altura_mm - HANDLE_SIZE / 2} />
          </>
        )}
      </g>
    </>
  )
}

function ResizeHandle({ painelNome, corner, x, y }: { painelNome: string; corner: Corner; x: number; y: number }) {
  const { setNodeRef, listeners, attributes, isDragging } = useDraggable({
    id: `resize-${painelNome}-${corner}`,
  })

  const cursor = corner === 'nw' || corner === 'se' ? 'nwse-resize' : 'nesw-resize'

  return (
    <g
      ref={(el) => setNodeRef(el as unknown as HTMLElement)}
      {...listeners}
      {...attributes}
      onClick={(e) => e.stopPropagation()}
      style={{ cursor, touchAction: 'none' }}
    >
      <rect
        x={x} y={y}
        width={HANDLE_SIZE} height={HANDLE_SIZE}
        fill={isDragging ? '#3b82f6' : 'white'}
        stroke="#3b82f6"
        strokeWidth="1.5"
        rx="1"
        style={{ pointerEvents: 'all' }}
      />
    </g>
  )
}

interface DraggableFerragemProps {
  ferragem: FerragemPosicao
  idx: number
  painelNome: string
  painelX: number
  painelY: number
  svgScale: number
  recorte: CanonicalRecorte | null
  isSelected: boolean
  onSelect: () => void
}

function DraggableFerragem({ ferragem, idx, painelNome, painelX, painelY, svgScale, recorte, isSelected, onSelect }: DraggableFerragemProps) {
  const { setNodeRef, listeners, attributes, transform, isDragging } = useDraggable({
    id: `ferragem-${painelNome}-${idx}`,
  })

  const dragOffsetX = transform ? transform.x / svgScale : 0
  const dragOffsetY = transform ? transform.y / svgScale : 0
  const cx = painelX + ferragem.x_mm + dragOffsetX
  const cy = painelY + ferragem.y_mm + dragOffsetY

  const cor = getCategoriaCor(recorte?.categoria)
  const fill = isDragging ? cor.fillDrag : cor.fill
  const labelY = cy  // computed per branch below

  const sharedG = {
    ref: (el: SVGGElement | null) => setNodeRef(el as unknown as HTMLElement),
    ...listeners,
    ...attributes,
    onClick: (e: React.MouseEvent) => { e.stopPropagation(); onSelect() },
    style: { cursor: isDragging ? 'grabbing' : 'grab', touchAction: 'none' as const },
  }

  const hasRecorte = recorte && recorte.recorte_largura_mm != null && recorte.recorte_altura_mm != null

  if (hasRecorte) {
    const w = recorte.recorte_largura_mm!
    const h = recorte.recorte_altura_mm!
    const rx = cx - w / 2
    const ry = cy - h / 2
    return (
      <g {...sharedG}>
        {isSelected && (
          <rect x={rx - 3} y={ry - 3} width={w + 6} height={h + 6}
            fill="none" stroke="white" strokeWidth="2.5" rx="2"
            style={{ pointerEvents: 'none' }} />
        )}
        {isSelected && (
          <rect x={rx - 3} y={ry - 3} width={w + 6} height={h + 6}
            fill="none" stroke={cor.stroke} strokeWidth="1.5" strokeDasharray="4 2" rx="2"
            style={{ pointerEvents: 'none' }} />
        )}
        <rect x={rx} y={ry} width={w} height={h}
          fill={fill} stroke={cor.stroke} strokeWidth={isDragging ? 2 : 1} rx="1"
          opacity={isDragging ? 0.85 : 1}
          style={{ pointerEvents: 'all' }}
        />
        <text x={cx} y={ry - 2} textAnchor="middle" fontSize="5" fill={cor.stroke}
          style={{ pointerEvents: 'none', userSelect: 'none' }}>
          {ferragem.codigo}
        </text>
        {isDragging && (
          <text x={cx} y={ry + h + 8} textAnchor="middle" fontSize="6" fill={cor.stroke}
            style={{ pointerEvents: 'none', userSelect: 'none' }}>
            {Math.round(ferragem.x_mm + dragOffsetX)},{Math.round(ferragem.y_mm + dragOffsetY)}
          </text>
        )}
      </g>
    )
  }

  // Fallback: círculo com label (recorte null ou ainda não carregado)
  return (
    <g {...sharedG}>
      {isSelected && (
        <circle cx={cx} cy={cy} r={11}
          fill="none" stroke="white" strokeWidth="2.5"
          style={{ pointerEvents: 'none' }} />
      )}
      {isSelected && (
        <circle cx={cx} cy={cy} r={11}
          fill="none" stroke={cor.stroke} strokeWidth="1.5" strokeDasharray="4 2"
          style={{ pointerEvents: 'none' }} />
      )}
      <circle cx={cx} cy={cy} r={6} fill={fill} stroke={cor.stroke} strokeWidth="1.5"
        style={{ pointerEvents: 'all' }} />
      <text x={cx} y={cy - 9} textAnchor="middle" fontSize="5" fill={cor.stroke}
        style={{ pointerEvents: 'none', userSelect: 'none' }}>
        {ferragem.codigo}
      </text>
      {isDragging && (
        <text x={cx} y={cy + 14} textAnchor="middle" fontSize="6" fill={cor.stroke}
          style={{ pointerEvents: 'none', userSelect: 'none' }}>
          {Math.round(ferragem.x_mm + dragOffsetX)},{Math.round(ferragem.y_mm + dragOffsetY)}
        </text>
      )}
    </g>
  )
}
