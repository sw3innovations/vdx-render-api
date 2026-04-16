// ─── Material types ───────────────────────────────────────────────────────────

export interface VidroMaterial {
  tipo: string
  cor: string
  opacidade: number
  transmission: number
  ior: number
  thickness: number
  roughness: number
  metalness: number
  clearcoat: number
  clearcoatRoughness: number
  envMapIntensity: number
  attenuationColor: string
  attenuationDistance: number
}

export interface FerragemMaterial {
  tipo: string
  cor: string
  roughness: number
  metalness: number
  clearcoat?: number
  clearcoatRoughness?: number
  envMapIntensity?: number
}

export interface VaoMaterial {
  tipo: string
  cor: string
  roughness: number
  metalness: number
}

// ─── Scene geometry ───────────────────────────────────────────────────────────

export interface Vec3 {
  x: number
  y: number
  z: number
}

export interface Animacao {
  tipo: 'pivotante' | 'deslizante' | 'basculante' | 'fixo'
  eixo?: 'x' | 'y' | 'z'
  angulo_max?: number
  angulo_min?: number
  ponto_pivo?: Vec3
  distancia_max?: number
}

export interface Geometria {
  tipo: 'box' | 'cylinder' | 'sphere'
  largura?: number
  altura?: number
  profundidade?: number
  raio?: number
  comprimento?: number
}

// ─── Scene objects ────────────────────────────────────────────────────────────

export interface VidroScene {
  id: string
  nome: string
  classificacao: 'movel' | 'fixo' | 'bandeira'
  largura: number
  altura: number
  espessura: number
  posicao: Vec3
  rotacao: Vec3
  material: VidroMaterial
  animacao?: Animacao
}

export interface FerragemScene {
  id: string
  nome: string
  codigo: string
  tipo: string
  peca_nome: string
  posicao: Vec3
  rotacao: Vec3
  geometria: Geometria
  material: FerragemMaterial
  recorte?: string
}

export interface Vao {
  largura: number
  altura: number
  profundidade: number
  material: VaoMaterial
}

export interface Dimensoes {
  largura: number
  altura: number
  espessura_vidro: number
}

export interface Piso {
  cor: string
  roughness: number
  metalness: number
  envMapIntensity: number
}

export interface CameraInicial {
  posicao: Vec3
  target: Vec3
}

export interface Ambiente {
  iluminacao: string
  toneMapping: string
  toneMappingExposure: number
  shadowMap: string
  antialias: boolean
  piso: Piso
  camera_inicial: CameraInicial
}

export interface SceneJSON {
  version: string
  tipologia: string
  layout: string
  dimensoes: Dimensoes
  unidade: string
  vidros: VidroScene[]
  ferragens: FerragemScene[]
  vao: Vao
  ambiente: Ambiente
}

// ─── Render response ──────────────────────────────────────────────────────────

export interface FerragemInfo {
  nome: string
  codigo: string
  tipo: string
  posicao?: Vec3
}

export interface PecaInfo {
  nome: string
  largura_mm: number
  altura_mm: number
  classificacao?: string
  ferragens: FerragemInfo[]
}

export interface RenderResponse {
  svg: string
  pecas: PecaInfo[]
  metadata: Record<string, unknown>
}

// ─── Tipologia ────────────────────────────────────────────────────────────────

export interface Tipologia {
  chave: string
  nome: string
  preview_url?: string
  cached?: boolean
  categoria?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

// ─── Request types ────────────────────────────────────────────────────────────

export interface PecaRequest {
  nome: string
  largura_mm: number
  altura_mm: number
}

export interface RenderRequest {
  tipologia_nome: string
  pecas: PecaRequest[]
  cor_vidro?: string
  espessura_vidro_mm?: number
}
