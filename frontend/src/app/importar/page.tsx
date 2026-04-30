'use client'

import { useState } from 'react'
import Link from 'next/link'
import { importarTipologia, isImportError } from '@/lib/import-api'
import type { ImportResult } from '@/lib/import-api'
import ImportTextarea from '@/components/import-textarea'
import ImportPreview from '@/components/import-preview'
import ImportFerragensList from '@/components/import-ferragens-list'
import ImportActions from '@/components/import-actions'
import ImportWarnings from '@/components/import-warnings'
import ImportErrorDisplay from '@/components/import-error'
import type { ImportError } from '@/lib/import-api'

export default function ImportarPage() {
  const [json, setJson] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState<ImportError | null>(null)

  async function handleSubmit() {
    setLoading(true)
    setError(null)
    setResult(null)

    const res = await importarTipologia(json)

    setLoading(false)
    if (isImportError(res)) {
      setError(res)
    } else {
      setResult(res)
    }
  }

  return (
    <div className="min-h-screen bg-[#F5F2EE]">
      <header className="bg-[#1a5276] text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-5 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Importar Tipologia</h1>
            <p className="text-blue-200 text-sm mt-0.5">
              Cole um JSON conforme o contrato v2 para gerar preview e downloads
            </p>
          </div>
          <nav className="hidden sm:flex gap-3 text-sm">
            <Link href="/" className="text-blue-200 hover:text-white transition-colors">
              Tipologias
            </Link>
            <Link href="/editor" className="text-blue-200 hover:text-white transition-colors">
              Editor
            </Link>
            <Link href="/smart" className="text-blue-200 hover:text-white transition-colors">
              Smart Vision
            </Link>
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Left: textarea + controls (40%) */}
          <div className="lg:w-[40%] shrink-0 flex flex-col gap-4">
            <ImportTextarea
              value={json}
              onChange={setJson}
              onSubmit={handleSubmit}
              loading={loading}
            />
            {error && <ImportErrorDisplay error={error} />}
          </div>

          {/* Right: preview + actions (60%) */}
          <div className="flex-1 flex flex-col gap-4">
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
          </div>
        </div>
      </main>
    </div>
  )
}
