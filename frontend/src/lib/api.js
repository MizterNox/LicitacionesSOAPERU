/**
 * Cliente API centralizado para LicitLens Frontend.
 * Gestiona URL base, serialización de parámetros, timeout y cabeceras.
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const TOKEN_STORAGE_KEY = 'access_token'
export const SESSION_EXPIRED_EVENT = 'auth:session-expired'

// Endpoints que nunca deben disparar el refresco automático (evita bucles infinitos)
const AUTH_NO_RETRY = ['/api/v1/auth/login', '/api/v1/auth/register', '/api/v1/auth/refresh', '/api/v1/auth/logout']

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_STORAGE_KEY),
  set: (t) => (t ? localStorage.setItem(TOKEN_STORAGE_KEY, t) : localStorage.removeItem(TOKEN_STORAGE_KEY)),
  clear: () => localStorage.removeItem(TOKEN_STORAGE_KEY),
}

/**
 * Convierte el `detail` de FastAPI (string o lista de errores Pydantic 422) en un mensaje legible.
 */
function formatErrorDetail(detail, fallback) {
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (d?.msg ? String(d.msg).replace(/^Value error, /, '') : JSON.stringify(d)))
      .join(' · ')
  }
  return fallback
}

// Promesa compartida: si varias peticiones reciben 401 a la vez, se hace un único refresh.
let refreshPromise = null

/**
 * Renueva el access token usando la cookie httpOnly del refresh token.
 * Devuelve el payload ({ access_token, user }) o null si la sesión caducó.
 */
export function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    })
      .then(async (res) => {
        if (!res.ok) return null
        const data = await res.json()
        if (data?.access_token) tokenStore.set(data.access_token)
        return data
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

function notifySessionExpired() {
  tokenStore.clear()
  window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT))
}

/**
 * Wrapper de fetch que maneja serialización de params, errores HTTP y
 * renovación silenciosa del access token ante un 401 (un único reintento).
 */
export async function apiFetch(endpoint, options = {}) {
  const { params, headers = {}, signal, _retried, ...rest } = options
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`

  let url = `${API_BASE_URL}${path}`

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

  const token = tokenStore.get()
  const defaultHeaders = {
    'Accept': 'application/json',
    ...(rest.body ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...headers,
  }

  const response = await fetch(url, {
    ...rest,
    headers: defaultHeaders,
    credentials: 'include',
    signal,
  })

  const isAuthEndpoint = AUTH_NO_RETRY.some((p) => path.startsWith(p))

  if (response.status === 401 && !isAuthEndpoint && !_retried) {
    // Solo intentamos renovar si había una sesión (token) previa
    if (token) {
      const refreshed = await refreshAccessToken()
      if (refreshed?.access_token) {
        return apiFetch(endpoint, { ...options, _retried: true })
      }
      notifySessionExpired()
    }
  }

  if (!response.ok) {
    let errorDetail = `HTTP Error ${response.status}`
    try {
      const errJson = await response.json()
      errorDetail = formatErrorDetail(errJson.detail, errorDetail)
    } catch {
      // ignore
    }
    if (response.status === 429) {
      const wait = response.headers.get('Retry-After')
      if (wait && !/\d+ segundos/.test(errorDetail)) errorDetail += ` (reintente en ${wait} s)`
    }
    const error = new Error(errorDetail)
    error.status = response.status
    throw error
  }

  if (response.status === 204) return null
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

  const buildHeaders = () => {
    const token = tokenStore.get()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  const url = `${API_BASE_URL}/api/licitaciones/export?${searchParams.toString()}`
  let response = await fetch(url, { headers: buildHeaders(), credentials: 'include' })

  if (response.status === 401 && tokenStore.get()) {
    const refreshed = await refreshAccessToken()
    if (refreshed?.access_token) {
      response = await fetch(url, { headers: buildHeaders(), credentials: 'include' })
    } else {
      notifySessionExpired()
    }
  }

  if (!response.ok) {
    let errorDetail = `Error al exportar (${response.status})`
    try {
      const errJson = await response.json()
      errorDetail = formatErrorDetail(errJson.detail, errorDetail)
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
  refresh: async () => {
    const data = await refreshAccessToken()
    if (!data?.access_token) {
      const err = new Error('Sesión expirada')
      err.status = 401
      throw err
    }
    return data
  },
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

/**
 * Endpoints administrativos (requieren sesión: el interceptor adjunta el token)
 */
export const adminApi = {
  getTiposConfig: (signal) => apiFetch('/api/v1/settings/tipos', { signal }),
  saveTiposConfig: (tipos_activos) =>
    apiFetch('/api/v1/settings/tipos', { method: 'POST', body: JSON.stringify({ tipos_activos }) }),
  triggerEtl: (payload, sync = true) =>
    apiFetch('/api/v1/etl/trigger', { method: 'POST', params: { sync }, body: JSON.stringify(payload) }),
  recalculateScoring: (sync = true) =>
    apiFetch('/api/v1/etl/recalculate-scoring', { method: 'POST', params: { sync } }),
  getCronStatus: (signal) => apiFetch('/api/v1/cron/status', { signal }),
  getCronHistory: (limit = 15, signal) => apiFetch('/api/v1/cron/history', { params: { limit }, signal }),
}

