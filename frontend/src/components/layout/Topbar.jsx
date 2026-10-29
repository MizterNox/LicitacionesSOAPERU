// Header superior: título derivado de React Router + buscador global + notificaciones + perfil.
// UrgentStrip: barra de plazos urgentes derivada de state.convocatorias.

import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useApp } from '../../store/AppState.jsx'
import { useAuth } from '../../store/AuthContext.jsx'
import { Icon } from '../ui/Icon.jsx'
import { daysUntil, fmtDateShort } from '../../utils/format.js'
import SearchBar from '../search/SearchBar.jsx'

export default function Topbar() {
  const { state, dispatch } = useApp()
  const { user, openAuthModal, logout } = useAuth()
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()

  const getPageTitle = () => {
    const p = location.pathname
    if (p.startsWith('/menores')) return 'Contrataciones Menores (≤ 8 UIT)'
    if (p.startsWith('/buscador')) return 'Buscador SEACE'
    if (p.startsWith('/licitaciones/')) return 'Detalle de Licitación'
    if (p.startsWith('/postulaciones')) return 'Mis Postulaciones'
    if (p.startsWith('/analitica')) return 'Analítica de Competidores'
    if (p.startsWith('/alertas')) return 'Centro de Alertas IA'
    if (p.startsWith('/config')) return 'Configuración del Sistema'
    return 'Dashboard General'
  }

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
    <header className="relative flex h-14 shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 md:px-5">
      {/* Vista de búsqueda móvil expandida */}
      {mobileSearchOpen ? (
        <div className="absolute inset-0 z-30 flex items-center gap-2 bg-white px-3 md:hidden">
          <SearchBar className="flex-1" />
          <button
            onClick={() => setMobileSearchOpen(false)}
            className="icon-btn shrink-0"
            title="Cerrar búsqueda"
          >
            <Icon name="x" className="h-5 w-5" />
          </button>
        </div>
      ) : null}

      <button onClick={() => dispatch({ type: 'TOGGLE_MOBILE_NAV' })} className="icon-btn lg:hidden" title="Abrir menú">
        <Icon name="menu" className="h-5 w-5" />
      </button>

      <div className="min-w-0 leading-tight">
        <h1 className="truncate text-[14px] font-bold text-slate-900">{getPageTitle()}</h1>
        <button
          type="button"
          onClick={() => navigate('/config')}
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

      {/* Buscador global con IA y autocompletado */}
      <SearchBar className="mx-auto hidden md:block" />

      <div className="ml-auto flex items-center gap-1 md:ml-0">
        <button
          onClick={() => setMobileSearchOpen(true)}
          className="icon-btn md:hidden"
          title="Buscar"
        >
          <Icon name="search" className="h-5 w-5" />
        </button>
        <button
          onClick={() => navigate('/alertas')}
          className="icon-btn relative"
          title="Ver Alertas IA"
        >
          <Icon name="bell" className="h-[18px] w-[18px]" />
          <span className="absolute right-1 top-1 grid h-4 min-w-[16px] place-items-center rounded-full bg-brand-500 px-1 text-[9px] font-bold text-white ring-2 ring-white">
            IA
          </span>
        </button>

        <span className="mx-1.5 hidden h-6 w-px bg-slate-200 sm:block"></span>

        {user ? (
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen((prev) => !prev)}
              className="flex items-center gap-2.5 rounded-lg p-1.5 transition-colors hover:bg-slate-100 xl:pr-2.5"
              title="Perfil de usuario"
            >
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-brand-500 to-fuchsia-500 text-[11px] font-bold text-white shadow-sm">
                {user.nombre
                  ? user.nombre.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()
                  : (user.email ? user.email.slice(0, 2).toUpperCase() : 'US')}
              </span>
              <span className="hidden text-left leading-tight xl:block">
                <span className="block max-w-[130px] truncate text-xs font-bold text-slate-800">
                  {user.nombre || user.email}
                </span>
                <span className="block max-w-[130px] truncate text-[10px] text-slate-400">
                  {user.empresa || 'Plan Alertas SEACE'}
                </span>
              </span>
              <Icon name="chevron-down" className="hidden h-3.5 w-3.5 text-slate-400 xl:block" />
            </button>

            {userMenuOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setUserMenuOpen(false)}
                />
                <div className="absolute right-0 top-full z-50 mt-1 w-56 rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl ring-1 ring-slate-900/5">
                  <div className="border-b border-slate-100 px-3 py-2">
                    <p className="truncate text-xs font-semibold text-slate-900">{user.nombre || 'Usuario'}</p>
                    <p className="truncate text-[11px] text-slate-500">{user.email}</p>
                    {user.empresa && (
                      <p className="mt-0.5 truncate text-[10px] font-medium text-brand-600">{user.empresa}</p>
                    )}
                  </div>
                  <div className="py-1">
                    <button
                      onClick={() => {
                        setUserMenuOpen(false)
                        navigate('/alertas')
                      }}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50 transition-colors"
                    >
                      <Icon name="bell" className="h-4 w-4 text-slate-400" />
                      Mis Alertas Guardadas
                    </button>
                    <button
                      onClick={() => {
                        setUserMenuOpen(false)
                        navigate('/config')
                      }}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50 transition-colors"
                    >
                      <Icon name="settings" className="h-4 w-4 text-slate-400" />
                      Configuración
                    </button>
                  </div>
                  <div className="border-t border-slate-100 pt-1">
                    <button
                      onClick={() => {
                        setUserMenuOpen(false)
                        logout()
                      }}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
                    >
                      <Icon name="log-out" className="h-4 w-4" />
                      Cerrar sesión
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        ) : (
          <button
            onClick={() => openAuthModal('login')}
            className="flex items-center gap-1.5 rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-brand-600 transition-colors"
          >
            <Icon name="user" className="h-3.5 w-3.5" />
            <span>Iniciar Sesión</span>
          </button>
        )}
      </div>
    </header>
  )
}

// Barra de plazos urgentes (calculada dinámicamente desde el backend)
export function UrgentStrip() {
  const { state, dispatch } = useApp()
  const navigate = useNavigate()
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
        onClick={() => {
          dispatch({ type: 'SET_FILTER', key: 'plazo', value: '48h' })
          navigate('/menores')
        }}
        className="ml-auto flex shrink-0 items-center gap-1 rounded-md px-2 py-1 font-bold text-amber-700 transition-colors hover:bg-amber-100"
      >
        Ver urgentes <Icon name="arrow-right" className="h-3 w-3" />
      </button>
    </div>
  )
}
