// App: Conexión reactiva global con FastAPI/PostgreSQL y renderizado de rutas.

import { useEffect } from 'react'
import { useApp } from './store/AppState.jsx'
import AppRoutes from './routes/AppRoutes.jsx'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const { state, dispatch } = useApp()
  const { filters, query } = state

  // 1. Cargar estado inicial de sincronización de cron, tipos activos y lista de rubros
  useEffect(() => {
    const fetchCronAndConfig = async () => {
      try {
        const resStatus = await fetch(`${API_BASE_URL}/api/v1/cron/status`)
        if (resStatus.ok) {
          const dataStatus = await resStatus.json()
          dispatch({ type: 'SET_CRON_STATUS', payload: dataStatus })
        }
        const resTipos = await fetch(`${API_BASE_URL}/api/v1/settings/tipos`)
        if (resTipos.ok) {
          const dataTipos = await resTipos.json()
          if (dataTipos.tipos_activos) {
            dispatch({ type: 'SET_TIPOS_CONFIG', payload: dataTipos.tipos_activos })
          }
        }
        const resRubros = await fetch(`${API_BASE_URL}/api/v1/rubros`)
        if (resRubros.ok) {
          const dataRubros = await resRubros.json()
          dispatch({ type: 'SET_RUBROS_LIST', payload: dataRubros })
        }
      } catch (e) {
        console.warn('No se pudo precargar estado de cron/settings/rubros:', e)
      }
    }
    fetchCronAndConfig()
  }, [dispatch])

  // 2. HOOK REACTIVO: Consume dinámicamente @app.get('/api/licitaciones') ante cambios de filtros
  useEffect(() => {
    const controller = new AbortController()
    const fetchLicitaciones = async () => {
      dispatch({ type: 'SET_LOADING', payload: true })
      try {
        const params = new URLSearchParams()

        // Estado (vigente / finalizado)
        if (filters.estado === 'Vigente') {
          params.append('vigentes', 'true')
        } else if (filters.estado === 'Finalizado') {
          params.append('vigentes', 'false')
        }

        // Tipo objeto (Servicios, Bienes, Obras, todos)
        if (filters.tipoObjeto && filters.tipoObjeto !== 'todos') {
          params.append('tipo', filters.tipoObjeto)
        } else {
          params.append('tipo', 'todos')
        }

        // Rubro clasificado por IA
        if (filters.rubro && filters.rubro !== 'todos') {
          params.append('rubro', filters.rubro)
        }

        // Región geográfica
        if (filters.region && filters.region !== 'todas') {
          params.append('region', filters.region)
        }

        // Entidad compradora
        if (filters.entidad && filters.entidad !== 'todas') {
          params.append('entidad', filters.entidad)
        }

        // Tipo de proceso (LP, CP, AS, MC, etc.)
        if (filters.tipo && filters.tipo !== 'Todos') {
          params.append('tipo_proceso', filters.tipo)
        }

        // Contrataciones menores (<= 8 UIT)
        if (filters.soloMenores) {
          params.append('solo_menores', 'true')
        }

        // Plazo urgente (48h, 7d, 30d)
        if (filters.plazo && filters.plazo !== 'todas') {
          params.append('plazo', filters.plazo)
        }

        // Rango de montos
        if (filters.valorMin) {
          params.append('monto_min', filters.valorMin)
        }
        if (filters.valorMax) {
          params.append('monto_max', filters.valorMax)
        }

        // Filtros SOAPERU S.R.L. (Líneas de negocio TI y relevancia)
        if (filters.primaryTag && filters.primaryTag !== 'todas') {
          params.append('primary_tag', filters.primaryTag)
        }
        if (filters.soloRelevantesTI) {
          params.append('min_score', '30')
        }

        // Fecha de publicación ('todos' o YYYY-MM-DD)
        params.append('fecha', filters.fecha || 'todos')

        // Búsqueda Full-Text Search
        if (query && query.trim()) {
          params.append('q', query.trim())
        }

        // Criterio de ordenamiento
        if (state.sort) {
          params.append('sort', state.sort)
        }

        const url = `${API_BASE_URL}/api/licitaciones?${params.toString()}`
        const res = await fetch(url, { signal: controller.signal })
        if (!res.ok) throw new Error(`HTTP Error ${res.status}`)
        const data = await res.json()

        const items = Array.isArray(data) ? data : (data.convocatorias || [])
        dispatch({ type: 'SET_CONVOCATORIAS', payload: items })
      } catch (err) {
        if (err.name === 'AbortError') return
        console.error('Error al consultar /api/licitaciones desde FastAPI:', err)
        dispatch({ type: 'SET_ERROR', payload: err.message })
      }
    }

    fetchLicitaciones()
    return () => {
      controller.abort()
    }
  }, [
    filters.estado,
    filters.tipoObjeto,
    filters.rubro,
    filters.region,
    filters.entidad,
    filters.tipo,
    filters.soloMenores,
    filters.plazo,
    filters.valorMin,
    filters.valorMax,
    filters.fecha,
    filters.primaryTag,
    filters.soloRelevantesTI,
    query,
    state.sort,
    dispatch
  ])

  return <AppRoutes />
}
