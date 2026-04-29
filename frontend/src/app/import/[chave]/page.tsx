'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { recuperarTipologia, isImportError } from '@/lib/import-api'
import type { ImportResult } from '@/lib/import-api'
import ImportPreview from '@/components/import-preview'
import ImportFerragensList from '@/components/import-ferragens-list'
import ImportActions from '@/components/import-actions'
import ImportWarnings from '@/components/import-warnings'
import ImportErrorDisplay from '@/components/import-error'
import type { ImportError } from '@/lib/import-api'

export default function ImportSharePage() {
  const params = useParams()
  const chave = String(params.chave)

  const [loading, setLoading] = useState(true)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState<ImportError | null>(null)

  useEffect(() => {
    recuperarTipologia(chave).then((res) => {
      setLoading(false)
      if (isImportError(res)) {
        setError(res)
      } else {
        setResult(res)
      }
    })
  }, [chave])

  return (
    <div className="min-h-screen bg-[#F5F2EE]">
      <header className="bg-[#1a5276] text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-5 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">VDX Glass Engine</h1>
            <p className="text-blue-200 text-sm mt-0.5">Projeto compartilhado</p>
          </div>
          <Link
            href="/importar"
            className="shrink-0 text-sm bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-xl transition-colors"
          >
            Criar meu projeto
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-6 flex flex-col gap-4">
        {error && <ImportErrorDisplay error={error} />}

        <ImportPreview svg={result?.svg ?? null} loading={loading} />

        {result && (
          <>
            {result.avisos.length > 0 && <ImportWarnings avisos={result.avisos} />}
            <ImportActions
              tipologiaChave={result.tipologia_chave}
              pngUrl={result.png_url}
              pdfUrl={result.pdf_url}
              viewer3dUrl={result.viewer_3d_url}
            />
            <ImportFerragensList ferragens={result.ferragens_resolvidas} />
          </>
        )}
      </main>
    </div>
  )
}
