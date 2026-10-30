// Estado global de la app: Context + useReducer (patrón store).
// Conectado reactivamente con la base de datos PostgreSQL mediante FastAPI.

import { createContext, useContext, useMemo, useReducer } from 'react'

export const getTodayDateString = () => {
  const d = new Date()
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

export const DEFAULT_FILTERS = {
  tipo: 'Todos', // 'Todos' | 'LP' | 'CP' | 'MS' | 'AS' | 'MC'
  entidad: 'todas',
  region: 'todas',
  estado: 'Vigente', // 'todos' | 'Vigente' | 'Finalizado' (Vigente por defecto)
  tipoObjeto: 'Servicios', // 'Servicios' por defecto para SOAPERU
  rubro: 'todos', // 'todos' | 'Tecnología y Software' | ...
  valorMin: '',
  valorMax: '',
  plazo: 'todas', // 'todas' | '48h' | '7d' | '30d'
  fecha: 'todos', // 'todos' por defecto para mostrar las convocatorias de la base de datos
  soloMenores: false, // True = filtra estrictamente licitaciones <= 8 UIT (S/ 42,800)
  primaryTag: 'todas', // 'todas' | 'ERP_ODOO' | 'BI_ANALITICA' | 'CIBERSEGURIDAD' | 'BACKUP_CONTINUIDAD' | 'MICROSOFT_CLOUD' | 'FACTURACION_ELECTRONICA' | 'DESARROLLO_SOFTWARE'
  soloRelevantesTI: false, // True = min_score >= 30
}

const initialState = {
  view: 'dashboard',
  convocatorias: [], // Se alimenta dinámicamente desde el endpoint /api/licitaciones
  isLoading: true,
  error: null,
  selectedId: null,
  sidebarCollapsed: false,
  mobileNavOpen: false,
  filtersOpen: true,
  query: '',
  sort: 'relevance', // 'relevance' | 'date' | 'match' | 'value' | 'deadline'
  filters: { ...DEFAULT_FILTERS },
  cronStatus: null, // Datos de la última ejecución del cron
  tiposConfig: ['Servicios', 'Bienes', 'Obras'], // Tipos activos
  rubrosList: [], // Lista de rubros obtenida desde /api/v1/rubros
}

function reducer(state, action) {
  switch (action.type) {
    case 'SET_CONVOCATORIAS':
      return {
        ...state,
        convocatorias: action.payload,
        selectedId: state.selectedId && action.payload.some((c) => c.id === state.selectedId) ? state.selectedId : null,
        isLoading: false,
        error: null,
      }
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload }
    case 'SET_ERROR':
      return { ...state, error: action.payload, isLoading: false }
    case 'SET_CRON_STATUS':
      return { ...state, cronStatus: action.payload }
    case 'SET_TIPOS_CONFIG':
      return { ...state, tiposConfig: action.payload }
    case 'SET_RUBROS_LIST':
      return { ...state, rubrosList: action.payload }
    case 'SET_VIEW':
      return { ...state, view: action.view, mobileNavOpen: false, selectedId: null }
    case 'SELECT_BID':
      return { ...state, selectedId: action.id }
    case 'CLOSE_DETAIL':
      return { ...state, selectedId: null }
    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarCollapsed: !state.sidebarCollapsed }
    case 'TOGGLE_MOBILE_NAV':
      return { ...state, mobileNavOpen: !state.mobileNavOpen }
    case 'CLOSE_MOBILE_NAV':
      return { ...state, mobileNavOpen: false }
    case 'TOGGLE_FILTERS':
      return { ...state, filtersOpen: !state.filtersOpen }
    case 'SET_QUERY':
      return { ...state, query: action.query }
    case 'SET_SORT':
      return { ...state, sort: action.sort }
    case 'SET_FILTER':
      return { ...state, filters: { ...state.filters, [action.key]: action.value } }
    case 'TOGGLE_SOLO_MENORES':
      return { ...state, filters: { ...state.filters, soloMenores: !state.filters.soloMenores } }
    case 'CLEAR_FILTERS':
      return { ...state, query: '', filters: { ...DEFAULT_FILTERS } }
    case 'VER_URGENTES':
      return { ...state, view: 'buscador', filters: { ...state.filters, plazo: '48h' } }
    default:
      return state
  }
}

const Ctx = createContext(null)

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  const value = useMemo(() => ({ state, dispatch }), [state])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useApp() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useApp debe usarse dentro de <AppProvider>')
  return ctx
}
