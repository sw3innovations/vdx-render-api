import type { Metadata } from 'next'
import ShareClient from './ShareClient'

interface ShareParams {
  id: string
}

interface ShareData {
  tipologia: string
  largura: number
  altura: number
  corVidro: string
}

function decodeShareData(id: string): ShareData | null {
  try {
    const decoded = Buffer.from(id, 'base64').toString('utf-8')
    const data = JSON.parse(decoded) as Partial<ShareData>
    if (!data.tipologia) return null
    return {
      tipologia: data.tipologia,
      largura: data.largura ?? 900,
      altura: data.altura ?? 2100,
      corVidro: data.corVidro ?? 'incolor',
    }
  } catch {
    return null
  }
}

export async function generateMetadata({
  params,
}: {
  params: ShareParams
}): Promise<Metadata> {
  const data = decodeShareData(params.id)
  if (!data) {
    return { title: 'VDX Glass Engine' }
  }

  const label = data.tipologia.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  const title = `${label} — ${data.largura}×${data.altura}mm | VDX Glass Engine`
  const description = `Configuração: ${label}, ${data.largura}×${data.altura}mm, vidro ${data.corVidro}`

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: 'website',
      siteName: 'VDX Glass Engine',
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
    },
  }
}

export default function SharePage({ params }: { params: ShareParams }) {
  const data = decodeShareData(params.id)

  if (!data) {
    return (
      <div className="min-h-screen bg-[#F5F2EE] flex items-center justify-center">
        <div className="text-center text-gray-500">
          <p className="text-lg font-medium">Link inválido</p>
          <p className="text-sm mt-1">O link de compartilhamento não pôde ser decodificado.</p>
          <a href="/" className="mt-4 inline-block text-[#1a5276] text-sm hover:underline">
            ← Voltar ao início
          </a>
        </div>
      </div>
    )
  }

  return <ShareClient data={data} />
}
