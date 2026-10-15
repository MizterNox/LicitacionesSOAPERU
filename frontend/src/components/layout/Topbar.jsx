// Header superior: título + buscador global + notificaciones + perfil.
// UrgentStrip: barra de plazos urgentes derivada de state.convocatorias.

import { useApp } from '../../store/AppState.jsx'
import { Icon } from '../ui/Icon.jsx'
import { daysUntil, fmtDateShort } from '../../utils/format.js'

export const PAGE_TITLES = {
  dashboard: 'Dashboard',
  buscador: 'Buscador SEACE',
  postulaciones: 'Mis Postulaciones',
  analitica: 'Analítica de Competidores',
  alertas: 'Alertas IA',
  config: 'Configuración',
}

export default function Topbar() {
  const { state, dispatch } = useApp()
  const lastRun = state.cronStatus?.ultima_ejecucion
  const syncLabel = lastRun?.iniciado_en
    ? (() => {
        try {
          const d = new Date(lastRun.iniciado_en)
          const fStr = d.toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' })
          const hStr = d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })
          const g = lastRun.total_guardados != null ? ` · ${lastRun.total_guardados} reg.` : ''
          return `Actualizado: ${fStr} ${hStr}${g}`
        } catch {
          return 'Sincronizado con SEACE'
        }
      })()
    : 'Sincronizado con SEACE'

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 md:px-5">
      <button onClick={() => dispatch({ type: 'TOGGLE_MOBILE_NAV' })} className="icon-btn lg:hidden" title="Abrir menú">
        <Icon name="menu" className="h-5 w-5" />
      </button>

      <div className="min-w-0 leading-tight">
        <h1 className="truncate text-[14px] font-bold text-slate-900">{PAGE_TITLES[state.view] ?? 'Dashboard'}</h1>
        <button
          type="button"
          onClick={() => dispatch({ type: 'SET_VIEW', view: 'config' })}
          className="mt-px hidden items-center gap-1.5 text-[11px] text-slate-500 hover:text-brand-600 transition-colors sm:flex text-left"
          title="Ver auditoría y detalles del cron en Configuración"
        >
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60"></span>
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
          </span>
          <span>{syncLabel}</span>
        </button>
      </div>

      {/* Buscador global */}
      <label className="relative mx-auto hidden w-full max-w-xl md:block">
        <Icon name="search" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="search"
          value={state.query}
          onChange={(e) => dispatch({ type: 'SET_QUERY', query: e.target.value })}
          placeholder="Buscar entidad, objeto, código de convocatoria…"
          className="field h-10 rounded-full bg-slate-50 pl-9 pr-16"
        />
        <kbd className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-bold text-slate-400 shadow-sm lg:block">
          Ctrl K
        </kbd>
      </label>

      <div className="ml-auto flex items-center gap-1 md:ml-0">
        <button className="icon-btn md:hidden" title="Buscar">
          <Icon name="search" className="h-5 w-5" />
        </button>
        <button className="icon-btn relative" title="Notificaciones (3)">
          <Icon name="bell" className="h-[18px] w-[18px]" />
          <span className="absolute right-1 top-1 grid h-4 min-w-[16px] place-items-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white ring-2 ring-white">
            3
          </span>
        </button>
        <span className="mx-1.5 hidden h-6 w-px bg-slate-200 sm:block"></span>
        <button className="flex items-center gap-2.5 rounded-lg p-1.5 transition-colors hover:bg-slate-100 xl:pr-2.5" title="Perfil de usuario">
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-brand-500 to-fuchsia-500 text-[11px] font-bold text-white">
            MG
          </span>
          <span className="hidden text-left leading-tight xl:block">
            <span className="block text-xs font-bold text-slate-800">María Gamarra</span>
            <span className="block text-[10px] text-slate-400">Plan Pro · 5 días de prueba</span>
          </span>
          <Icon name="chevron-down" className="hidden h-3.5 w-3.5 text-slate-400 xl:block" />
        </button>
      </div>
    </header>
  )
}

// Barra de plazos urgentes (calculada dinámicamente desde el backend)
export function UrgentStrip() {
  const { state, dispatch } = useApp()
  const convocatorias = state.convocatorias || []
  const urgent = convocatorias.filter((c) => {
    if (c.estado !== 'Vigente' || !c.fecha_limite) return false
    const d = daysUntil(c.fecha_limite)
    return d >= 0 && d <= 2
  })

  if (urgent.length === 0) return null

  const next = urgent.reduce((a, b) => (daysUntil(a.fecha_limite) <= daysUntil(b.fecha_limite) ? a : b))

  return (
    <div className="flex h-9 shrink-0 items-center gap-2 overflow-hidden border-b border-amber-100 bg-amber-50/90 px-4 text-xs md:px-5" role="status">
      <span className="shrink-0 text-amber-600">
        <Icon name="clock" className="h-3.5 w-3.5" />
      </span>
      <p className="truncate text-amber-800">
        <span className="font-bold">Plazos urgentes:</span> {urgent.length} licitación{urgent.length === 1 ? '' : 'es'} en
        tu lista cierra{urgent.length === 1 ? '' : 'n'} en menos de 48 h
        {next ? (
          <>
            {' '}
            — próxima: <span className="font-bold">{next.codigo_seace}</span> ({fmtDateShort(next.fecha_limite)})
          </>
        ) : (
          '.'
        )}
      </p>
      <button
        onClick={() => dispatch({ type: 'VER_URGENTES' })}
        className="ml-auto flex shrink-0 items-center gap-1 rounded-md px-2 py-1 font-bold text-amber-700 transition-colors hover:bg-amber-100"
      >
        Ver urgentes <Icon name="arrow-right" className="h-3 w-3" />
      </button>
    </div>
  )
}
