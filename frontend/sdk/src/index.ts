// ─── Components ───────────────────────────────────────────────────────────────
export { VDXViewer } from './VDXViewer'
export { VDXPreview } from './VDXPreview'

// ─── API Client ───────────────────────────────────────────────────────────────
export { VDXClient, autoPecas } from './api-client'
export type { VDXClientOptions } from './api-client'

// ─── Types ────────────────────────────────────────────────────────────────────
export type {
  // Materials
  VidroMaterial,
  FerragemMaterial,
  VaoMaterial,

  // Geometry
  Vec3,
  Animacao,
  Geometria,

  // Scene objects
  VidroScene,
  FerragemScene,
  Vao,
  Dimensoes,
  Piso,
  CameraInicial,
  Ambiente,
  SceneJSON,

  // Render
  FerragemInfo,
  PecaInfo,
  RenderResponse,

  // Tipologia
  Tipologia,
  PaginatedResponse,

  // Requests
  PecaRequest,
  RenderRequest,

  // Proposal
  ProposalItem,
  Empresa,
  Cliente,
  ProposalRequest,
  ProposalResponse,

  // Chat / Feedback
  ChatMessage,
  ChatRequest,
  ChatResponse,
  FeedbackRequest,
  FeedbackResponse,

  // Health
  HealthResponse,
  HealthDetailedResponse,

  // Component props
  VDXViewerProps,
  VDXPreviewProps,
} from './types'
