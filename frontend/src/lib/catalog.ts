export const TIPOLOGIAS_V1 = [
  'porta_abrir',
  'porta_pivotante_simples',
  'porta_correr_2_folhas',
  'porta_correr_3_folhas',
  'janela_correr_2_folhas',
  'janela_basculante',
  'janela_maxim_ar',
  'box_de_giro',
  'box_canto_90',
  'box_frontal_2_folhas',
] as const

export const THUMB_DIMS: Record<string, { largura: number; altura: number }> = {
  porta_abrir:             { largura: 900,  altura: 2100 },
  porta_pivotante_simples: { largura: 1000, altura: 2400 },
  porta_correr_2_folhas:   { largura: 1800, altura: 2100 },
  porta_correr_3_folhas:   { largura: 2400, altura: 2100 },
  janela_correr_2_folhas:  { largura: 1200, altura: 1200 },
  janela_basculante:       { largura: 800,  altura: 500  },
  janela_maxim_ar:         { largura: 600,  altura: 600  },
  box_de_giro:             { largura: 800,  altura: 2000 },
  box_canto_90:            { largura: 900,  altura: 2000 },
  box_frontal_2_folhas:    { largura: 1200, altura: 2000 },
}
