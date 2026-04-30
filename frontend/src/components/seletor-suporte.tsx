'use client'

import type { FerragemSelecionada } from '@/lib/types'
import SeletorFerragem from './seletor-ferragem'

interface SeletorSuporteProps {
  selected: FerragemSelecionada | null
  onSelect: (f: FerragemSelecionada | null) => void
}

export default function SeletorSuporte({ selected, onSelect }: SeletorSuporteProps) {
  return <SeletorFerragem tipo="suporte" label="Suporte" selected={selected} onSelect={onSelect} />
}
