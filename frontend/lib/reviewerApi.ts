import { getAccessToken } from './supabase'

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
).replace(/\/+$/, '')

// =============================================================================
// Types
// =============================================================================

export type ReviewerRole = 'intake' | 'reviewer' | 'supervisor' | 'auditor'

export interface ReviewerIdentity {
  user_id: string
  email: string | null
  org_id: string
  org_name: string
  municipality: string
  role: ReviewerRole
  can_write: boolean
  active_ruleset_id: string | null
}

/** Categorical only. There is deliberately no numeric confidence anywhere. */
export type Band = 'alta' | 'media' | 'baja'

export type OcrStatus =
  | 'pendiente'
  | 'texto_incrustado'
  | 'sin_texto'
  | 'parcial'
  | 'error'

export type ProcessingStatus =
  | 'recibido'
  | 'extrayendo'
  | 'clasificando'
  | 'listo'
  | 'error'

export interface CaseRecord {
  id: string
  case_number: string
  permit_type: string
  applicant_name: string | null
  property_address: string | null
  catastro: string | null
  status: string
  assigned_reviewer_id: string | null
  ruleset_version_id: string
  profile: CaseProfile
  filing_date: string | null
  created_at: string
  updated_at: string
}

export interface CaseDocument {
  id: string
  case_id: string
  filename: string
  doc_type: string
  doc_type_label: string
  doc_type_source: 'pendiente' | 'modelo' | 'revisor'
  classification_band: Band | null
  classification_reason: string | null
  classification_page: number | null
  sha256: string
  page_count: number | null
  text_char_count: number | null
  ocr_status: OcrStatus
  processing_status: ProcessingStatus
  processing_error: string | null
  uploaded_at: string
}

export interface DocumentType {
  code: string
  name: string
  description: string
}

export interface AuditEvent {
  id: string
  event_type: string
  object_ref: string | null
  payload: Record<string, unknown>
  actor_user_id: string | null
  created_at: string
}

export interface UploadOutcome {
  documents: CaseDocument[]
  rejected: { filename: string; reason: string }[]
}


// =============================================================================
// Checks, facts, profile
// =============================================================================

/** The three decision states. Identifiers are fixed; never invent a fourth. */
export type CheckStatus =
  | 'sin_hallazgos'
  | 'hallazgo_identificado'
  | 'requiere_criterio'

export type RuleFamily = 'presencia' | 'vigencia' | 'consistencia' | 'aplicabilidad'

export interface Citation {
  field_key: string
  document_id: string | null
  page: number | null
  value: string | null
  band: Band
}

export interface ComplianceCheck {
  id: string
  rule_id: string
  rule_code: string | null
  rule_title: string | null
  rule_citation: string | null
  authority: string | null
  severity: 'leve' | 'moderada' | 'grave' | null
  family: RuleFamily
  status: CheckStatus
  band: Band
  reason_code: string | null
  explanation: string
  evidence_ids: string[]
  citations: Citation[]
  evaluated_at: string
}

export interface CheckSummary {
  sin_hallazgos: number
  hallazgo_identificado: number
  requiere_criterio: number
  total_evaluadas: number
}

export interface ExtractedFactRow {
  id: string
  document_id: string | null
  field_key: string
  value_text: string | null
  value_date: string | null
  source_page: number | null
  band: Band
  status: 'extraido' | 'evidencia_no_disponible' | 'contradictorio'
  extracted_at: string
}

/** One recorded external lookup, and how trustworthy the result is. */
export type QualityFlag =
  | 'ok'
  | 'sin_resultado'
  | 'ambiguo'
  | 'fuera_de_servicio'
  | 'esquema_inesperado'

export interface GisOutcome {
  resultado: string
  consultas: {
    source: string
    quality_flag: QualityFlag
    matched: boolean | null
    nota: string | null
    valor: string | null
  }[]
}

export interface ExtractionOutcome {
  procesados: {
    document_id: string
    doc_type: string
    campos: number
    localizados: number
    error: string | null
  }[]
  omitidos: { document_id: string; reason: string }[]
  campos_totales: number
}

/**
 * The answers that decide which rules apply.
 * An unanswered key is never read as "no": the rule escalates instead.
 */
export interface CaseProfile {
  forma_juridica?: 'persona_natural' | 'entidad_juridica'
  tenencia?: 'dueno' | 'arrendatario'
  tipo_tramite?: 'nueva' | 'renovacion'
  categoria_uso?:
    | 'alimentos'
    | 'salud'
    | 'comercio_general'
    | 'entretenimiento'
    | 'industrial'
  acceso_publico?: boolean
  radica_representante?: boolean
}

export interface RequerimientoHallazgo {
  numero: number
  rule_code: string
  titulo: string
  severidad: string
  parrafo: string
  subsanacion: string
  fundamento: string | null
  /** 'modelo' when drafted automatically, 'sistema' when the engine wrote it. */
  generado: 'modelo' | 'sistema'
  /** Why an automatically drafted paragraph was rejected, when it was. */
  descartado_por: string | null
  evidencia: { documento: string; pagina: number; valor: string | null }[]
}

export interface Requerimiento {
  id: string
  case_id: string
  version: number
  status: 'borrador' | 'aprobado' | 'descartado'
  finding_ids: string[]
  body: {
    encabezado: Record<string, string | null>
    introduccion: string
    hallazgos: RequerimientoHallazgo[]
    cierre: string
    pendientes_de_criterio: { rule_code: string | null }[]
  }
  model_used: string | null
  generated_at: string
  approved_at: string | null
  generated_by: string | null
  approved_by: string | null
}

// =============================================================================
// Transport
// =============================================================================

/** Base URL, for the few places that build a link rather than fetch. */
export function getApiBase(): string {
  return API_BASE_URL
}

async function authHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken()
  if (!token) throw new Error('Su sesion expiro. Vuelva a iniciar sesion.')
  return { Authorization: `Bearer ${token}` }
}

async function readError(response: Response): Promise<string> {
  const body = await response.json().catch(() => null)
  return body?.detail || `Error ${response.status}`
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    ...(await authHeaders()),
    ...options.headers,
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers })

  if (!response.ok) throw new Error(await readError(response))
  if (response.status === 204) return null as T
  return response.json()
}

// =============================================================================
// API
// =============================================================================

export const reviewerApi = {
  /**
   * Who the caller is on the reviewer side.
   * Returns null when they are not a member of any permit office - which is the
   * normal case for applicant accounts, not an error.
   */
  async me(): Promise<ReviewerIdentity | null> {
    try {
      const headers = await authHeaders()
      const response = await fetch(`${API_BASE_URL}/reviewer/me`, { headers })
      if (response.status === 403 || response.status === 503) return null
      if (!response.ok) throw new Error(await readError(response))
      return response.json()
    } catch {
      return null
    }
  },

  taxonomy: () => request<DocumentType[]>('/reviewer/taxonomy'),

  listCases: (status?: string) =>
    request<CaseRecord[]>(
      `/reviewer/cases${status ? `?status_filter=${encodeURIComponent(status)}` : ''}`
    ),

  nextCaseNumber: () =>
    request<{ case_number: string }>('/reviewer/cases/next-number'),

  createCase: (data: {
    case_number?: string
    applicant_name?: string
    property_address?: string
    catastro?: string
  }) =>
    request<CaseRecord>('/reviewer/cases', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getCase: (id: string) =>
    request<{ case: CaseRecord; documents: CaseDocument[] }>(`/reviewer/cases/${id}`),

  updateCase: (id: string, data: Record<string, unknown>) =>
    request<CaseRecord>(`/reviewer/cases/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  auditTrail: (caseId: string) =>
    request<AuditEvent[]>(`/reviewer/cases/${caseId}/audit`),

  /**
   * Upload PDFs to a case.
   * Note the absent Content-Type: the browser must set the multipart boundary.
   */
  async uploadDocuments(caseId: string, files: File[]): Promise<UploadOutcome> {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))

    const response = await fetch(`${API_BASE_URL}/reviewer/cases/${caseId}/documents`, {
      method: 'POST',
      headers: await authHeaders(),
      body: form,
    })

    if (!response.ok) throw new Error(await readError(response))
    return response.json()
  },

  extract: (caseId: string) =>
    request<ExtractionOutcome>(`/reviewer/cases/${caseId}/extract`, { method: 'POST' }),

  gis: (caseId: string) =>
    request<GisOutcome>(`/reviewer/cases/${caseId}/gis`, { method: 'POST' }),

  evaluate: (caseId: string) =>
    request<{ resumen: CheckSummary; ruleset_id: string }>(
      `/reviewer/cases/${caseId}/evaluate`,
      { method: 'POST' }
    ),

  checks: (caseId: string) =>
    request<{ resumen: CheckSummary; verificaciones: ComplianceCheck[] }>(
      `/reviewer/cases/${caseId}/checks`
    ),

  facts: (caseId: string) =>
    request<{ campos: ExtractedFactRow[] }>(`/reviewer/cases/${caseId}/facts`),

  draftRequerimiento: (caseId: string) =>
    request<Requerimiento>(`/reviewer/cases/${caseId}/requerimiento`, {
      method: 'POST',
    }),

  getRequerimiento: (caseId: string) =>
    request<Requerimiento | Record<string, never>>(
      `/reviewer/cases/${caseId}/requerimiento`
    ),

  approveRequerimiento: (id: string) =>
    request<Requerimiento>(`/reviewer/requerimientos/${id}/approve`, {
      method: 'POST',
    }),

  documentUrl: (documentId: string) =>
    request<{ url: string; expires_in: number }>(`/reviewer/documents/${documentId}/url`),

  setDocumentType: (documentId: string, docType: string) =>
    request<CaseDocument>(`/reviewer/documents/${documentId}`, {
      method: 'PATCH',
      body: JSON.stringify({ doc_type: docType }),
    }),
}

// =============================================================================
// Display helpers
// =============================================================================

/**
 * The three decision states, with their exact Spanish strings.
 *
 * These labels are fixed by policy. Do not paraphrase them, and never render the
 * words "COMPLIANT" or "NON-COMPLIANT" anywhere in this product.
 */
export const DECISION_STATES = {
  sin_hallazgos: 'Sin hallazgos en las verificaciones cubiertas',
  hallazgo_identificado: 'Hallazgo identificado — ver evidencia',
  requiere_criterio: 'Requiere criterio del revisor',
} as const

export const BAND_LABELS: Record<Band, string> = {
  alta: 'Confianza alta',
  media: 'Confianza media',
  baja: 'Confianza baja',
}

export const OCR_LABELS: Record<OcrStatus, string> = {
  pendiente: 'Sin procesar',
  texto_incrustado: 'Texto digital',
  parcial: 'Texto parcial',
  sin_texto: 'Escaneado (sin texto)',
  error: 'No se pudo leer',
}

export const PROCESSING_LABELS: Record<ProcessingStatus, string> = {
  recibido: 'Recibido',
  extrayendo: 'Extrayendo texto',
  clasificando: 'Clasificando',
  listo: 'Listo',
  error: 'Requiere atencion',
}

export const CASE_STATUS_LABELS: Record<string, string> = {
  recibido: 'Recibido',
  en_revision: 'En revision',
  borrador_requerimiento: 'Borrador de requerimiento',
  cerrado: 'Cerrado',
}

export const FAMILY_LABELS: Record<RuleFamily, string> = {
  presencia: 'Presencia',
  vigencia: 'Vigencia',
  consistencia: 'Consistencia',
  aplicabilidad: 'Aplicabilidad',
}

/**
 * Why a check escalated. These come from the engine, not from a model, and each
 * one names a specific trigger.
 */
export const REASON_LABELS: Record<string, string> = {
  aplicabilidad_indeterminada: 'No se pudo determinar si la regla aplica',
  condicion_de_revision: 'La regla exige revision manual',
  condiciones_no_concluyentes: 'La evidencia no permite concluir',
  hallazgo_sin_evidencia: 'No hay evidencia que sustente un hallazgo',
  inconsistencia_sin_ambos_documentos: 'Falta uno de los dos documentos a comparar',
  regla_sin_fundamento_legal: 'La regla no tiene fundamento legal registrado',
  banda_baja: 'La lectura de la evidencia es poco confiable',
  error_de_evaluacion: 'La regla no se pudo evaluar',
}

/**
 * What a lookup's quality flag means for the reviewer. Anything but `ok` makes
 * the rules that depend on it escalate rather than conclude.
 */
export const QUALITY_LABELS: Record<QualityFlag, string> = {
  ok: 'Consulta completada',
  sin_resultado: 'El servicio no devolvio un resultado',
  ambiguo: 'Resultado ambiguo — confirme manualmente',
  fuera_de_servicio: 'El servicio no estuvo disponible',
  esquema_inesperado: 'El servicio respondio en un formato inesperado',
}

export const GIS_SOURCE_LABELS: Record<string, string> = {
  zonificacion: 'Calificacion del predio (MIPR)',
  crim_parcelas: 'Parcela (CRIM)',
}

export const FACT_STATUS_LABELS: Record<string, string> = {
  extraido: 'Leido',
  evidencia_no_disponible: 'No localizado',
  contradictorio: 'Lecturas contradictorias',
}

export function formatDate(value: string): string {
  try {
    return new Date(value).toLocaleString('es-PR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}
