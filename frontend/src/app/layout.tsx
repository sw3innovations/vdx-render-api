import type { Metadata, Viewport } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'VDX Glass Engine',
  description: 'Configurador de esquadrias de vidro — visualização 3D fotorrealista',
  manifest: '/manifest.json',
}

export const viewport: Viewport = {
  themeColor: '#1a5276',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-[#F5F2EE]">{children}</body>
    </html>
  )
}
