'use client'

import type { FerragemSelecionada } from '@/lib/types'
import SeletorFerragem from './seletor-ferragem'

interface SeletorDobradicaProps {
  selected: FerragemSelecionada | null
  onSelect: (f: FerragemSelecionada | null) => void
}

export default function SeletorDobradica({ selected, onSelect }: SeletorDobradicaProps) {
  return <SeletorFerragem tipo="dobradica" label="Dobradiça" selected={selected} onSelect={onSelect} />
}
