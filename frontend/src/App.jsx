// App: layout split-screen [Sidebar | (Contenido | Panel de Detalle)]
// Conectado dinámicamente con FastAPI y PostgreSQL

import { useEffect } from 'react'
import { useApp } from './store/AppState.jsx'
import { useSelectedConvocatoria, useVisibleConvocatorias } from './store/selectors.js'
import Sidebar from './components/layout/Sidebar.jsx'
import Topbar, { UrgentStrip } from './components/layout/Topbar.jsx'
import KpiRow from './components/dashboard/KpiRow.jsx'
import FilterBar from './components/dashboard/FilterBar.jsx'
import BiddingTable from './components/dashboard/BiddingTable.jsx'
import DetailPanel from './components/dashboard/DetailPanel.jsx'
import ConfigView from './components/config/ConfigView.jsx'
import { AnalyticsView } from './components/analytics/AnalyticsView.jsx'
import AlertsView from './components/alerts/AlertsView.jsx'
import AuthModal from './components/auth/AuthModal.jsx'
import { Icon } from './components/ui/Icon.jsx'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const VIEW_META = {
  dashboard: {
    icon: 'layout-dashboard',
    title: 'Dashboard',
    desc: 'Tu centro de mando: métricas, sugerencias de IA y el listado de oportunidades del SEACE.',
  },
  buscador: {
    icon: 'search',
    title: 'Buscador SEACE',
    desc: 'Explora la base completa de convocatorias con filtros avanzados y búsqueda inteligente.',
  },
  postulaciones: {
    icon: 'kanban',
    title: 'Mis Postulaciones',
    desc: 'Pipeline de tus postulaciones: borrador, enviada, en calificación, buena pro.',
  },
  analitica: {
    icon: 'chart',
    title: 'Analítica de Competidores',
    desc: 'Benchmark contra competidores: historial de buenas pro, precios y regiones.',
  },
  alertas: {
    icon: 'bell',
    title: 'Alertas IA',
    desc: 'Alertas en tiempo real generadas por IA según el perfil de tu empresa.',
  },
  config: {
    icon: 'settings',
    title: 'Configuración',
    desc: 'Configura tu perfil, criterios de relevancia y preferencias de la plataforma.',
  },
}

function PlaceholderView({ view }) {
  const { dispatch } = useApp()
  const m = VIEW_META[view]
  return (
    <div className="mx-auto max-w-[1560px] p-4 md:p-6">
      <div className="card grid min-h-[60vh] place-items-center p-10 text-center">
        <div className="max-w-sm">
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-brand-50 text-brand-600">
            <Icon name={m.icon} className="h-6 w-6" />
          </span>
          <h2 className="mt-4 text-lg font-bold text-slate-900">{m.title}</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-500">{m.desc}</p>
          <p className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1 text-[11px] font-bold text-amber-700">
            Módulo en construcción · próxima iteración
          </p>
          <div className="mt-5">
            <button onClick={() => dispatch({ type: 'SET_VIEW', view: 'dashboard' })} className="btn-primary">
              <Icon name="layout-dashboard" className="h-4 w-4" /> Volver al dashboard
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function MainContent() {
  const { state } = useApp()
  const rows = useVisibleConvocatorias()
  if (state.view === 'dashboard' || state.view === 'buscador') {
    return (
      <div className="mx-auto max-w-[1560px] space-y-4 p-4 md:space-y-5 md:p-6">
        <KpiRow />
        <FilterBar />
        <BiddingTable rows={rows} />
      </div>
    )
  }
  if (state.view === 'analitica') {
    return <AnalyticsView />
  }
  if (state.view === 'alertas') {
    return <AlertsView />
  }
  if (state.view === 'config') {
    return <ConfigView />
  }
  return <PlaceholderView view={state.view} />
}

export default function App() {
  const { state, dispatch } = useApp()
  const selected = useSelectedConvocatoria()
  const { filters, query } = state

  // Cargar estado inicial de sincronización de cron, tipos activos y lista de rubros
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

  // =========================================================================
  // HOOK REACTIVO: Consume dinámicamente @app.get('/api/licitaciones')
  // =========================================================================
  useEffect(() => {
    let isMounted = true
    const fetchLicitaciones = async () => {
      dispatch({ type: 'SET_LOADING', payload: true })
      try {
        const params = new URLSearchParams()

        // 1. Mapeo de vigentes (booleano)
        if (filters.estado === 'Vigente') {
          params.append('vigentes', 'true')
        } else if (filters.estado === 'Finalizado') {
          params.append('vigentes', 'false')
        }

        // 2. Mapeo de tipo (Bienes, Servicios, Obras, todos)
        if (filters.tipoObjeto && filters.tipoObjeto !== 'todos') {
          params.append('tipo', filters.tipoObjeto)
        } else {
          params.append('tipo', 'todos')
        }

        // 3. Mapeo de rubro IA
        if (filters.rubro && filters.rubro !== 'todos') {
          params.append('rubro', filters.rubro)
        }

        // 4. Mapeo de fecha ('hoy' por defecto o 'todos')
        params.append('fecha', filters.fecha || 'todos')

        // 5. Búsqueda por texto (Full-Text Search) si existe
        if (query && query.trim()) {
          params.append('q', query.trim())
        }

        const url = `${API_BASE_URL}/api/licitaciones?${params.toString()}`
        const res = await fetch(url)
        if (!res.ok) throw new Error(`HTTP Error ${res.status}`)
        const data = await res.json()

        if (isMounted) {
          const items = Array.isArray(data) ? data : (data.convocatorias || [])
          dispatch({ type: 'SET_CONVOCATORIAS', payload: items })
        }
      } catch (err) {
        console.error('Error al consultar /api/licitaciones desde FastAPI:', err)
        if (isMounted) {
          dispatch({ type: 'SET_ERROR', payload: err.message })
        }
      }
    }

    fetchLicitaciones()
    return () => {
      isMounted = false
    }
  }, [filters.estado, filters.tipoObjeto, filters.rubro, filters.fecha, query, dispatch])

  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== 'Escape') return
      if (state.mobileNavOpen) dispatch({ type: 'CLOSE_MOBILE_NAV' })
      else if (state.selectedId != null) dispatch({ type: 'CLOSE_DETAIL' })
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [state.mobileNavOpen, state.selectedId, dispatch])

  const showDetail = selected && (state.view === 'dashboard' || state.view === 'buscador')

  return (
    <div className="flex h-full min-h-0">
      <Sidebar />
      {state.mobileNavOpen && (
        <div
          className="fixed inset-0 z-40 bg-ink-950/60 backdrop-blur-[2px] lg:hidden"
          onClick={() => dispatch({ type: 'CLOSE_MOBILE_NAV' })}
        />
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <UrgentStrip />
        <main className="flex min-h-0 flex-1">
          <section className="scroll-thin min-w-0 flex-1 overflow-y-auto">
            <MainContent />
          </section>
          {showDetail && (
            <>
              <div
                className="fixed inset-0 z-40 bg-slate-950/40 backdrop-blur-[2px] xl:hidden"
                onClick={() => dispatch({ type: 'CLOSE_DETAIL' })}
              />
              <DetailPanel bid={selected} />
            </>
          )}
        </main>
      </div>
      <AuthModal />
    </div>
  )
}
