import { getAccessToken } from './supabase'

// Remove trailing slash from base URL to prevent double-slash issue
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')

// Export for use in components that build URLs directly
export function getApiUrl(endpoint: string): string {
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  return `${API_BASE_URL}${normalizedEndpoint}`
}

async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const token = await getAccessToken()

  if (!token) {
    throw new Error('No authentication token - user may need to log in again')
  }

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...options.headers,
  }

  // Ensure endpoint starts with / and no double slashes
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  const url = `${API_BASE_URL}${normalizedEndpoint}`

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Error desconocido' }))
    throw new Error(error.detail || `HTTP error ${response.status}`)
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null
  }

  return response.json()
}

// Projects
export const projectsApi = {
  list: () => fetchWithAuth('/projects'),

  get: (id: string) => fetchWithAuth(`/projects/${id}`),

  create: (data: {
    name: string
    address?: string
    municipality?: string
    catastro_number?: string
    calificacion?: string
    zoning_code?: string
    notes?: string
  }) => fetchWithAuth('/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  update: (id: string, data: Partial<{
    name: string
    address: string
    municipality: string
    catastro_number: string
    calificacion: string
    zoning_code: string
    status: string
    notes: string
  }>) => fetchWithAuth(`/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  delete: (id: string) => fetchWithAuth(`/projects/${id}`, {
    method: 'DELETE',
  }),

  validateFase1: (projectId: string, projectDescription: string, districtCode: string) =>
    fetchWithAuth(`/projects/${projectId}/validate_fase1`, {
      method: 'POST',
      body: JSON.stringify({
        project_description: projectDescription,
        district_code: districtCode,
      }),
    }),
}

// Validations
export const validationsApi = {
  list: (projectId?: string, limit: number = 50) => {
    const params = new URLSearchParams()
    if (projectId) params.set('project_id', projectId)
    params.set('limit', limit.toString())
    return fetchWithAuth(`/validations?${params}`)
  },

  get: (id: string) => fetchWithAuth(`/validations/${id}`),

  getPdfUrl: (id: string) => getApiUrl(`/validations/${id}/report.pdf`),

  getStats: (): Promise<UsageStats> => fetchWithAuth('/validations/stats'),
}

// Folders
export const foldersApi = {
  list: () => fetchWithAuth('/folders'),

  get: (id: string) => fetchWithAuth(`/folders/${id}`),

  create: (name: string) => fetchWithAuth('/folders', {
    method: 'POST',
    body: JSON.stringify({ name }),
  }),

  delete: (id: string) => fetchWithAuth(`/folders/${id}`, {
    method: 'DELETE',
  }),

  listItems: (folderId: string) => fetchWithAuth(`/folders/${folderId}/items`),

  addItem: (folderId: string, validationId: string) =>
    fetchWithAuth(`/folders/${folderId}/items`, {
      method: 'POST',
      body: JSON.stringify({ validation_id: validationId }),
    }),

  removeItem: (folderId: string, itemId: string) =>
    fetchWithAuth(`/folders/${folderId}/items/${itemId}`, {
      method: 'DELETE',
    }),
}

// Types
export interface Project {
  id: string
  user_id: string
  name: string
  address: string | null
  municipality: string | null
  catastro_number: string | null
  calificacion: string | null
  zoning_code: string | null
  status: string | null
  phase1_completed: boolean
  phase1_result: Record<string, unknown> | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface ValidationListItem {
  id: string
  user_id: string
  project_id: string | null
  validation_type: string
  viable: boolean
  project_description: string | null
  property_address: string | null
  created_at: string
  project_name: string | null
  project_address: string | null
  project_municipality: string | null
}

export interface Validation extends ValidationListItem {
  result: Record<string, unknown>
}

export interface Folder {
  id: string
  user_id: string
  name: string
  created_at: string
  item_count: number
}

export interface FolderItem {
  id: string
  folder_id: string
  validation_id: string
  created_at: string
  project_name: string | null
  project_address: string | null
  validation_date: string | null
  viable: boolean
}

export interface UsageStats {
  period: string
  total_validations: number
  viable_validations: number
  non_viable_validations: number
}

// PCOC Validation types
export interface PCOCValidation {
  id: string
  user_id: string
  project_id: string | null
  project_name: string | null
  property_address: string | null
  municipality: string | null
  zoning_code: string | null
  current_step: number
  status: string
  filter1_data: Record<string, unknown> | null
  filter2_data: Record<string, unknown> | null
  filter3_data: Record<string, unknown> | null
  filter4_data: Record<string, unknown> | null
  result: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface ExemptCategory {
  code: string
  name_es: string
  name_en: string
  section: string
}

export interface DistrictParameters {
  code: string
  name_es: string
  name_en: string
  category: string
  parameters: {
    max_height: string | null
    max_coverage: string | null
    min_lot_size: string | null
  }
}

// PCOC API
export const pcocApi = {
  list: (limit: number = 50): Promise<PCOCValidation[]> =>
    fetchWithAuth(`/pcoc?limit=${limit}`),

  get: (id: string): Promise<PCOCValidation> =>
    fetchWithAuth(`/pcoc/${id}`),

  create: (data: {
    project_id?: string
    project_name?: string
    property_address?: string
    municipality?: string
    zoning_code?: string
  }): Promise<PCOCValidation> =>
    fetchWithAuth('/pcoc', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Partial<PCOCValidation>): Promise<PCOCValidation> =>
    fetchWithAuth(`/pcoc/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchWithAuth(`/pcoc/${id}`, { method: 'DELETE' }),

  getExemptCategories: (): Promise<{ obras_exentas: ExemptCategory[]; obras_menores: ExemptCategory[] }> =>
    fetchWithAuth('/pcoc/exempt-categories'),

  getDistrictParameters: (zoningCode: string): Promise<DistrictParameters> =>
    fetchWithAuth(`/pcoc/district-parameters/${zoningCode}`),

  analyzeFilter1: (id: string) =>
    fetchWithAuth(`/pcoc/${id}/analyze-filter1`, { method: 'POST' }),

  analyzeFilter2: (id: string) =>
    fetchWithAuth(`/pcoc/${id}/analyze-filter2`, { method: 'POST' }),

  analyzeFilter3: (id: string) =>
    fetchWithAuth(`/pcoc/${id}/analyze-filter3`, { method: 'POST' }),

  analyzeFilter4: (id: string) =>
    fetchWithAuth(`/pcoc/${id}/analyze-filter4`, { method: 'POST' }),

  generateResult: (id: string) =>
    fetchWithAuth(`/pcoc/${id}/generate-result`, { method: 'POST' }),

  getPdfUrl: (id: string) => getApiUrl(`/pcoc/${id}/report.pdf`),
}

// Document Validation types
export interface DocumentStatus {
  required: boolean
  optional: boolean
  conditional: string | null
  uploaded: boolean
  file_url: string | null
  file_name: string | null
  verified: boolean
  notes: string
}

export interface MemorialExplicativo {
  generated: boolean
  project_description: string | null
  location_description: string | null
  zoning_info: string | null
  construction_details: string | null
  environmental_compliance: string | null
  permit_type_justification: string | null
  additional_notes: string | null
  pdf_url: string | null
}

export interface DocumentValidation {
  id: string
  user_id: string
  pcoc_validation_id: string | null
  validation_type: string
  project_name: string | null
  property_address: string | null
  municipality: string | null
  status: string
  documents: Record<string, DocumentStatus> | null
  memorial_explicativo: MemorialExplicativo | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface DocumentRequirement {
  code: string
  name: string
  description: string
  required: boolean
  conditional: string | null
}

export interface DocumentValidationResult {
  is_complete: boolean
  total_required: number
  total_optional: number
  uploaded_required: number
  uploaded_optional: number
  verified_required: number
  verified_optional: number
  missing_required: Array<{ code: string; name: string; description: string }>
  missing_optional: Array<{ code: string; name: string; description: string; conditional: string | null }>
  progress_percent: number
}

// Document Validation API
export const documentsApi = {
  list: (validationType?: string, limit: number = 50): Promise<DocumentValidation[]> => {
    const params = new URLSearchParams()
    if (validationType) params.set('validation_type', validationType)
    params.set('limit', limit.toString())
    return fetchWithAuth(`/documents?${params}`)
  },

  get: (id: string): Promise<DocumentValidation> =>
    fetchWithAuth(`/documents/${id}`),

  create: (data: {
    pcoc_validation_id?: string
    validation_type?: string
    project_name?: string
    property_address?: string
    municipality?: string
  }): Promise<DocumentValidation> =>
    fetchWithAuth('/documents', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Partial<DocumentValidation>): Promise<DocumentValidation> =>
    fetchWithAuth(`/documents/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchWithAuth(`/documents/${id}`, { method: 'DELETE' }),

  getPCOCRequirements: (): Promise<DocumentRequirement[]> =>
    fetchWithAuth('/documents/requirements/pcoc'),

  getPermisoUnicoRequirements: (): Promise<DocumentRequirement[]> =>
    fetchWithAuth('/documents/requirements/permiso-unico'),

  updateDocumentStatus: (
    id: string,
    docCode: string,
    data: {
      uploaded?: boolean
      file_url?: string
      file_name?: string
      verified?: boolean
      notes?: string
    }
  ) => {
    const params = new URLSearchParams()
    if (data.uploaded !== undefined) params.set('uploaded', String(data.uploaded))
    if (data.file_url) params.set('file_url', data.file_url)
    if (data.file_name) params.set('file_name', data.file_name)
    if (data.verified !== undefined) params.set('verified', String(data.verified))
    if (data.notes) params.set('notes', data.notes)
    return fetchWithAuth(`/documents/${id}/update-document/${docCode}?${params}`, { method: 'POST' })
  },

  validate: (id: string): Promise<{ validation_result: DocumentValidationResult; status: string }> =>
    fetchWithAuth(`/documents/${id}/validate`, { method: 'POST' }),

  generateMemorial: (id: string): Promise<{ memorial_explicativo: MemorialExplicativo }> =>
    fetchWithAuth(`/documents/${id}/generate-memorial`, { method: 'POST' }),
}

// Billing / Subscription types
export interface Subscription {
  user_id: string
  tier: 'free' | 'professional' | 'empresarial'
  status: 'active' | 'inactive' | 'canceled' | 'past_due' | 'trialing' | 'incomplete'
  stripe_customer_id: string | null
  stripe_subscription_id: string | null
  current_period_end: string | null
}

// Billing API
export const billingApi = {
  getSubscription: (): Promise<Subscription> =>
    fetchWithAuth('/billing/subscription'),

  createCheckoutSession: (tier: 'professional' | 'empresarial', period: 'monthly' | 'annual'): Promise<{ url: string }> =>
    fetchWithAuth('/billing/create-checkout-session', {
      method: 'POST',
      body: JSON.stringify({ tier, period }),
    }),

  createPortalSession: (): Promise<{ url: string }> =>
    fetchWithAuth('/billing/create-portal-session', {
      method: 'POST',
    }),
}
