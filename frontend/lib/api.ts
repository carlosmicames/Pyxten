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
