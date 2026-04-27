interface PreviewPuxadorSVGProps {
  nome: string
  size?: number
  color?: string
}

function detectShape(nome: string): 'circulo' | 'barra' | 'cilindro' {
  const n = nome.toLowerCase()
  if (n.includes('diâmetro') || n.includes('diametro') || n.includes('circular') || n.includes('knob')) {
    return 'circulo'
  }
  if (n.includes('barra') || n.includes('bar')) {
    return 'barra'
  }
  return 'cilindro'
}

export default function PreviewPuxadorSVG({ nome, size = 80, color = '#90B0C8' }: PreviewPuxadorSVGProps) {
  const shape = detectShape(nome)
  const cx = size / 2
  const cy = size / 2

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} fill="none" xmlns="http://www.w3.org/2000/svg">
      {shape === 'circulo' && (
        <>
          <circle cx={cx} cy={cy} r={size * 0.32} fill={color} opacity={0.9} />
          <circle cx={cx} cy={cy} r={size * 0.18} fill="white" opacity={0.35} />
          <circle cx={cx} cy={cy} r={size * 0.32} stroke={color} strokeWidth={1.5} strokeOpacity={0.6} />
        </>
      )}
      {shape === 'barra' && (
        <>
          <rect
            x={size * 0.12} y={size * 0.38}
            width={size * 0.76} height={size * 0.24}
            rx={size * 0.12}
            fill={color} opacity={0.9}
          />
          <rect
            x={size * 0.12} y={size * 0.38}
            width={size * 0.76} height={size * 0.10}
            rx={size * 0.05}
            fill="white" opacity={0.25}
          />
        </>
      )}
      {shape === 'cilindro' && (
        <>
          <rect
            x={size * 0.36} y={size * 0.14}
            width={size * 0.28} height={size * 0.72}
            rx={size * 0.14}
            fill={color} opacity={0.9}
          />
          <rect
            x={size * 0.40} y={size * 0.14}
            width={size * 0.10} height={size * 0.72}
            rx={size * 0.05}
            fill="white" opacity={0.25}
          />
        </>
      )}
    </svg>
  )
}
