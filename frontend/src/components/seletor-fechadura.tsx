'use client'

import type { FerragemSelecionada } from '@/lib/types'
import SeletorFerragem from './seletor-ferragem'

interface SeletorFechaduraProps {
  selected: FerragemSelecionada | null
  onSelect: (f: FerragemSelecionada | null) => void
}

export default function SeletorFechadura({ selected, onSelect }: SeletorFechaduraProps) {
  return <SeletorFerragem tipo="fechadura" label="Fechadura" selected={selected} onSelect={onSelect} />
}
