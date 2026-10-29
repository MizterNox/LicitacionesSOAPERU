/**
 * Cliente API centralizado para LicitLens Frontend.
 * Gestiona URL base, serialización de parámetros, timeout y cabeceras.
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Wrapper de fetch que maneja serialización de params y errores HTTP.
 */
export async function apiFetch(endpoint, options = {}) {
  const { params, headers = {}, signal, ...rest } = options

  let url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`

  if (params) {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        searchParams.append(key, String(val))
      }
    })
    const qs = searchParams.toString()
    if (qs) {
      url += (url.includes('?') ? '&' : '?') + qs
    }
  }

  const token = localStorage.getItem('access_token')
  const defaultHeaders = {
    'Accept': 'application/json',
    ...(rest.body ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...headers,
  }

  const response = await fetch(url, {
    ...rest,
    headers: defaultHeaders,
    signal,
  })

  if (!response.ok) {
    let errorDetail = `HTTP Error ${response.status}`
    try {
      const errJson = await response.json()
      if (errJson.detail) errorDetail = errJson.detail
    } catch {
      // ignore
    }
    const error = new Error(errorDetail)
    error.status = response.status
    throw error
  }

  return response.json()
}

/**
 * Descarga de archivo de exportación (CSV o XLSX)
 */
export async function downloadExport(format = 'csv', filters = {}) {
  const searchParams = new URLSearchParams()
  searchParams.append('format', format)

  Object.entries(filters).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      searchParams.append(key, String(val))
    }
  })

  const token = localStorage.getItem('access_token')
  const headers = token ? { Authorization: `Bearer ${token}` } : {}

  const url = `${API_BASE_URL}/api/licitaciones/export?${searchParams.toString()}`
  const response = await fetch(url, { headers })

  if (!response.ok) {
    let errorDetail = `Error al exportar (${response.status})`
    try {
      const errJson = await response.json()
      if (errJson.detail) errorDetail = errJson.detail
    } catch {
      // ignore
    }
    throw new Error(errorDetail)
  }

  const disposition = response.headers.get('Content-Disposition')
  let filename = `licitaciones_${format}.${format}`
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename="?([^";]+)"?/)
    if (match && match[1]) {
      filename = match[1]
    }
  }

  const blob = await response.blob()
  const downloadUrl = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = downloadUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(downloadUrl)
}

/**
 * Endpoints específicos de convocatorias
 */
export const tendersApi = {
  getLicitaciones: (filters = {}, signal) => apiFetch('/api/licitaciones', { params: filters, signal }),
  getLicitacionDetail: (ocid, signal) => apiFetch(`/api/licitaciones/${ocid}`, { signal }),
  getSuggestions: (q, signal) => apiFetch('/api/v1/search/suggest', { params: { q }, signal }),
  getRubros: (signal) => apiFetch('/api/v1/rubros', { signal }),
  getMonthlyMetrics: (meses = 12, groupBy = 'tipo', signal) =>
    apiFetch('/api/v1/metrics/monthly', { params: { meses, group_by: groupBy }, signal }),
  getMetricsSummary: (signal) => apiFetch('/api/v1/metrics/summary', { signal }),
  downloadExport,
}

/**
 * Endpoints de autenticación y perfil
 */
export const authApi = {
  register: (payload) => apiFetch('/api/v1/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload) => apiFetch('/api/v1/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  refresh: () => apiFetch('/api/v1/auth/refresh', { method: 'POST' }),
  logout: () => apiFetch('/api/v1/auth/logout', { method: 'POST' }),
  getMe: (signal) => apiFetch('/api/v1/auth/me', { signal }),
}

/**
 * Endpoints de filtros favoritos y alertas IA
 */
export const alertsApi = {
  getSavedFilters: (signal) => apiFetch('/api/v1/me/filters', { signal }),
  createSavedFilter: (payload) => apiFetch('/api/v1/me/filters', { method: 'POST', body: JSON.stringify(payload) }),
  updateSavedFilter: (id, payload) => apiFetch(`/api/v1/me/filters/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteSavedFilter: (id) => apiFetch(`/api/v1/me/filters/${id}`, { method: 'DELETE' }),
  getAlertsHistory: (limit = 20, signal) => apiFetch('/api/v1/me/alerts/history', { params: { limit }, signal }),
  sendTestAlert: () => apiFetch('/api/v1/me/alerts/test', { method: 'POST' }),
}

