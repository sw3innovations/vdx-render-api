type Props = {
  tipologiaChave: string
  pngUrl: string | null
  pdfUrl: string | null
  viewer3dUrl: string | null
}

export default function ImportActions({ tipologiaChave, pngUrl, pdfUrl, viewer3dUrl }: Props) {
  const shareUrl = `https://render.sw3.tec.br/import/${tipologiaChave}`
  const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(`Veja o projeto no VDX Glass Engine: ${shareUrl}`)}`

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 flex flex-col gap-2">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Downloads e compartilhamento</p>

      <div className="grid grid-cols-2 gap-2">
        <a
          href={pngUrl ?? '#'}
          download
          aria-disabled={!pngUrl}
          className={`flex items-center justify-center gap-1.5 text-sm px-3 py-2 rounded-lg font-medium transition-colors ${
            pngUrl
              ? 'bg-[#1a5276] text-white hover:bg-[#154360]'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed pointer-events-none'
          }`}
        >
          <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path d="M10 2a1 1 0 011 1v9.586l2.293-2.293a1 1 0 011.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L9 12.586V3a1 1 0 011-1z" />
            <path d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" />
          </svg>
          PNG
        </a>

        <a
          href={pdfUrl ?? '#'}
          download
          aria-disabled={!pdfUrl}
          className={`flex items-center justify-center gap-1.5 text-sm px-3 py-2 rounded-lg font-medium transition-colors ${
            pdfUrl
              ? 'bg-[#1a5276] text-white hover:bg-[#154360]'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed pointer-events-none'
          }`}
        >
          <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path d="M10 2a1 1 0 011 1v9.586l2.293-2.293a1 1 0 011.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L9 12.586V3a1 1 0 011-1z" />
            <path d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" />
          </svg>
          PDF
        </a>

        <a
          href={viewer3dUrl ?? '#'}
          target="_blank"
          rel="noopener noreferrer"
          aria-disabled={!viewer3dUrl}
          className={`flex items-center justify-center gap-1.5 text-sm px-3 py-2 rounded-lg font-medium transition-colors ${
            viewer3dUrl
              ? 'border border-[#1a5276] text-[#1a5276] hover:bg-[#1a5276]/5'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed pointer-events-none'
          }`}
        >
          <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path d="M10 2L2 7l8 5 8-5-8-5zM2 13l8 5 8-5M2 10l8 5 8-5" stroke="currentColor" strokeWidth="1.5" fill="none" />
          </svg>
          Ver em 3D
        </a>

        <a
          href={whatsappUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-1.5 text-sm px-3 py-2 rounded-lg font-medium border border-green-500 text-green-600 hover:bg-green-50 transition-colors"
        >
          <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path d="M10 .4A9.6 9.6 0 00.4 10c0 1.68.44 3.26 1.2 4.62L.4 19.6l5.16-1.17A9.6 9.6 0 1010 .4zm0 17.6a8 8 0 01-4.08-1.12l-.29-.17-3.06.7.71-2.98-.19-.3A8 8 0 1110 18z" />
            <path d="M7.3 6.4c-.18-.4-.37-.41-.54-.42H6.3c-.18 0-.48.07-.73.34C5.32 6.6 4.6 7.3 4.6 8.7s1 2.76 1.14 2.95c.14.19 1.96 3.12 4.83 4.25 2.87 1.13 2.87.75 3.39.7.52-.05 1.66-.68 1.9-1.33.23-.65.23-1.2.16-1.33-.07-.12-.26-.19-.55-.33-.29-.14-1.66-.82-1.92-.91-.26-.09-.45-.14-.64.14-.19.28-.73.91-.9 1.1-.16.19-.33.21-.62.07-.29-.14-1.22-.45-2.33-1.44-.86-.77-1.44-1.72-1.61-2.01-.17-.29-.02-.45.13-.59.13-.13.29-.33.43-.5.14-.16.19-.28.28-.47.1-.19.05-.35-.02-.49-.07-.14-.62-1.5-.86-2.06z" />
          </svg>
          WhatsApp
        </a>
      </div>

      <div className="mt-1 flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2">
        <span className="text-xs text-gray-500 truncate flex-1">{shareUrl}</span>
        <button
          type="button"
          onClick={() => navigator.clipboard.writeText(shareUrl)}
          className="text-xs text-[#1a5276] hover:underline shrink-0"
        >
          Copiar
        </button>
      </div>
    </div>
  )
}
