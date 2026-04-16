import { useEffect, useState } from 'react'
import type { VDXPreviewProps } from './types'

/**
 * VDXPreview — lightweight SVG preview component.
 *
 * Fetches the server-rendered SVG for a tipologia and displays it.
 * No Three.js dependency — ideal for catalogs, lists, and thumbnails.
 *
 * @example
 * ```tsx
 * const client = new VDXClient('my-api-key')
 * <VDXPreview client={client} tipologia="porta_pivotante_simples" width={200} height={300} />
 * ```
 */
export function VDXPreview({
  client,
  tipologia,
  className = '',
  width = 200,
  height = 300,
  onLoad,
  onError,
}: VDXPreviewProps) {
  const [svgContent, setSvgContent] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError(null)
    setSvgContent(null)

    client
      .getTipologiaPreviewSvg(tipologia)
      .then((svg) => {
        if (cancelled) return
        setSvgContent(svg)
        setIsLoading(false)
        onLoad?.()
      })
      .catch((err: unknown) => {
        if (cancelled) return
        const msg = err instanceof Error ? err.message : String(err)
        setError(msg)
        setIsLoading(false)
        onError?.(err instanceof Error ? err : new Error(msg))
      })

    return () => { cancelled = true }
  }, [client, tipologia, onLoad, onError])

  const containerStyle: React.CSSProperties = {
    width,
    height,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    position: 'relative',
  }

  if (isLoading) {
    return (
      <div style={containerStyle} className={className}>
        <div style={{
          width: 24, height: 24,
          border: '3px solid rgba(0,0,0,0.1)',
          borderTopColor: '#1a5276',
          borderRadius: '50%',
          animation: 'vdx-preview-spin 0.8s linear infinite',
        }} />
        <style>{`@keyframes vdx-preview-spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  if (error) {
    return (
      <div
        style={{ ...containerStyle, background: '#fef2f2', color: '#dc2626', fontSize: 12 }}
        className={className}
        title={error}
      >
        ⚠ Erro ao carregar preview
      </div>
    )
  }

  if (!svgContent) return null

  return (
    <div
      className={className}
      style={containerStyle}
      dangerouslySetInnerHTML={{ __html: svgContent }}
    />
  )
}
