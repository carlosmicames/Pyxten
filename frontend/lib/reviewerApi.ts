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
// Transport
// =============================================================================

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
