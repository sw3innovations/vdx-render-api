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
  classificacao: 'movel' | 'fixo' | 'bandeira' | 'fixa' | 'correr'
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

/** Full 3D scene descriptor (v2.0 with PBR materials). */
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

// ─── Render / API response types ──────────────────────────────────────────────

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

// ─── Smart Vision ─────────────────────────────────────────────────────────────

export interface VisionAnalysis {
  tipologia_sugerida: string
  largura_mm: number
  altura_mm: number
  tipo_abertura: string
  num_folhas: number
  espessura_vidro_mm: number
  cor_vidro: string
  observacoes: string
  confianca: number
}

export interface SmartProjectResponse {
  analise: VisionAnalysis
  tipologia_chave: string
  svg: string
  scene: SceneJSON
  pecas: Record<string, unknown>[]
  ferragens: Record<string, unknown>[]
  kit?: Record<string, unknown> | null
  viewer_url?: string | null
  viewer_token?: string | null
  viewer_expires_in?: number | null
  engine: string
  versao_api: string
}

export interface PhotoToProjectRequest {
  image_base64: string
  contexto?: string
  cor_vidro?: string
  espessura_vidro_mm?: number
}

export interface SketchToProjectRequest {
  image_base64: string
  notas?: string
  cor_vidro?: string
  espessura_vidro_mm?: number
}

export interface TextToProjectRequest {
  descricao: string
  fabricante?: string
  cor_vidro?: string
  espessura_vidro_mm?: number
}

// ─── Proposal types ───────────────────────────────────────────────────────────

export interface ProposalItem {
  descricao: string
  tipologia?: string
  largura_mm?: number
  altura_mm?: number
  espessura_vidro_mm?: number
  cor_vidro?: string
  quantidade?: number
  valor_unitario?: number
  valor_total?: number
  notas?: string
}

export interface Empresa {
  nome: string
  cnpj?: string
  endereco?: string
  telefone?: string
  email?: string
  website?: string
  logo_base64?: string
}

export interface Cliente {
  nome: string
  email?: string
  telefone?: string
  cpf_cnpj?: string
  endereco?: string
}

export interface ProposalRequest {
  numero_proposta?: string
  empresa: Empresa
  cliente: Cliente
  itens: ProposalItem[]
  observacoes?: string
  validade_dias?: number
  condicoes_pagamento?: string
  prazo_entrega?: string
}

export interface ProposalResponse {
  numero_proposta: string
  total_itens: number
  valor_total: number | null
  pdf_bytes: number
  validade_ate: string
}

// ─── Chat / Feedback ──────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  messages: ChatMessage[]
  tipologia_contexto?: string
}

export interface ChatResponse {
  reply: string
  sugestoes?: string[]
}

export interface FeedbackRequest {
  tipologia: string
  rating: number
  comentario?: string
  dados_renderizacao?: Record<string, unknown>
}

export interface FeedbackResponse {
  id: number
  recebido: boolean
}

// ─── Health ───────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
  version?: string
}

export interface HealthDetailedResponse {
  status: string
  db: string
  cache?: string
  version?: string
  uptime_s?: number
}

// ─── Viewer component props ───────────────────────────────────────────────────

export interface VDXViewerProps {
  /** API client instance */
  client: import('./api-client').VDXClient
  /** Tipologia key, e.g. "porta_pivotante_simples" */
  tipologia: string
  /** Total width in mm */
  largura: number
  /** Total height in mm */
  altura: number
  /** Glass color key: "incolor" | "verde" | "fume" | "bronze" | "espelho" */
  corVidro?: string
  /** Glass thickness in mm (default: 8) */
  espessura?: number
  /** CSS class for the container div */
  className?: string
  /** Called with a PNG Blob when user clicks screenshot */
  onScreenshot?: (blob: Blob) => void
  /** Called when 3D scene finishes loading */
  onReady?: () => void
  /** Called when scene JSON loads (useful for embedding) */
  onSceneLoad?: (scene: SceneJSON) => void
}

export interface VDXPreviewProps {
  /** API client instance */
  client: import('./api-client').VDXClient
  /** Tipologia key */
  tipologia: string
  /** CSS class for the container */
  className?: string
  /** Width in px for the SVG element */
  width?: number
  /** Height in px for the SVG element */
  height?: number
  /** Called when SVG loads */
  onLoad?: () => void
  /** Called on error */
  onError?: (err: Error) => void
}
