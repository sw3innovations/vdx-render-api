import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDim(v: number): string {
  return `${Math.round(v)} mm`
}

export function tipologiaLabel(chave: string): string {
  return chave.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function categoriaFromChave(chave: string): string {
  if (chave.includes('porta')) return 'Portas'
  if (chave.includes('janela')) return 'Janelas'
  if (chave.includes('box')) return 'Box'
  return 'Outros'
}
