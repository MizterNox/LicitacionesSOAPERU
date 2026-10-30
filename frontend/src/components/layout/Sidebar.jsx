// Sidebar de navegación profesional (superficie oscura "ink").
// Soporte para React Router (NavLink) y acceso prioritario al nicho de Contrataciones Menores.

import { NavLink } from 'react-router-dom'
import { useApp } from '../../store/AppState.jsx'
import { useAuth } from '../../store/AuthContext.jsx'
import { Icon, LogoMark } from '../ui/Icon.jsx'

const NAV = [
  {
    section: 'Principal',
    items: [
      { path: '/dashboard', label: 'Dashboard', icon: 'layout-dashboard' }
    ],
  },
  {
    section: 'Operaciones',
    items: [
      { path: '/menores', label: 'Contrataciones Menores', icon: 'zap', badge: '≤ 8 UIT', highlight: true },
      { path: '/buscador', label: 'Buscador SEACE', icon: 'search' },
      { path: '/analitica', label: 'Analítica de Mercado', icon: 'chart' },
    ],
  },
  {
    section: 'Inteligencia',
    items: [{ path: '/alertas', label: 'Alertas IA', icon: 'bell', badge: 'IA', live: true }],
  },
  {
    section: 'Sistema',
    items: [{ path: '/config', label: 'Configuración', icon: 'settings' }],
  },
]

function NavItem({ it, collapsed }) {
  const { dispatch } = useApp()
  return (
    <NavLink
      to={it.path}
      title={it.label}
      onClick={() => dispatch({ type: 'CLOSE_MOBILE_NAV' })}
      className={({ isActive }) =>
        `group relative flex h-9 items-center gap-3 rounded-lg text-[13px] font-semibold transition-colors ${
          collapsed ? 'justify-center px-0' : 'px-3'
        } ${
          isActive
            ? 'bg-brand-500/20 text-white font-bold'
            : 'text-ink-300 hover:bg-white/[0.06] hover:text-white'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive && <span className="absolute left-0 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-r-full bg-brand-400"></span>}
          <span className={isActive ? 'text-brand-300' : 'text-ink-400 transition-colors group-hover:text-ink-100'}>
            <Icon name={it.icon} className="h-[18px] w-[18px] shrink-0" />
          </span>
          <span className={`min-w-0 flex-1 truncate ${collapsed ? 'hidden' : ''}`}>{it.label}</span>
          {it.badge && !collapsed && (
            <span
              className={`ml-auto shrink-0 rounded-full px-1.5 py-px text-[10px] font-bold ${
                it.highlight
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  : it.live
                  ? 'bg-red-500/15 text-red-300'
                  : 'bg-white/10 text-ink-200'
              }`}
            >
              {it.badge}
            </span>
          )}
          {it.badge && collapsed && <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-brand-400"></span>}
        </>
      )}
    </NavLink>
  )
}

export default function Sidebar() {
  const { state, dispatch } = useApp()
  const { user, openAuthModal, logout } = useAuth()
  const c = state.sidebarCollapsed

  return (
    <aside
      className={`relative z-50 flex h-full w-[280px] shrink-0 flex-col border-r border-ink-800 bg-ink-950 text-ink-100 transition-all duration-200 max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:shadow-2xl ${
        state.mobileNavOpen ? 'max-lg:translate-x-0' : 'max-lg:-translate-x-full'
      } max-lg:transition-transform lg:${c ? 'w-[78px]' : 'w-[264px]'}`}
      aria-label="Navegación principal"
    >
      {/* Logo */}
      <div className={`flex h-14 shrink-0 items-center gap-2.5 border-b border-white/5 ${c ? 'justify-center px-0' : 'px-3 sm:px-4'}`}>
        <LogoMark className="h-8 w-8 shrink-0" />
        <div className={`min-w-0 leading-tight ${c ? 'hidden' : ''}`}>
          <p className="truncate text-[15px] font-extrabold tracking-tight text-white">LicitLens</p>
          <p className="truncate text-[10px] font-semibold uppercase tracking-[0.16em] text-ink-400">SEACE · Perú</p>
        </div>
        <button
          onClick={() => dispatch({ type: 'TOGGLE_SIDEBAR' })}
          className="icon-btn-dark ml-auto hidden shrink-0 lg:inline-flex"
          title={c ? 'Expandir menú' : 'Colapsar menú'}
        >
          <Icon name="chevrons-left" className={`h-4 w-4 transition-transform duration-200 ${c ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Navegación */}
      <nav className="sidebar-scroll flex-1 space-y-5 overflow-y-auto px-3 py-4">
        {NAV.map((sec) => (
          <div key={sec.section}>
            <p className={`mb-1.5 px-3 text-[10px] font-bold uppercase tracking-[0.14em] text-ink-500 ${c ? 'hidden' : ''}`}>
              {sec.section}
            </p>
            <div className="space-y-0.5">
              {sec.items.map((it) => (
                <NavItem key={it.path} it={it} collapsed={c} />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Radar IA + usuario */}
      <div className={`shrink-0 space-y-3 px-3 pb-4 ${c ? 'hidden' : ''}`}>
        <div className="relative overflow-hidden rounded-xl border border-brand-500/25 bg-gradient-to-br from-brand-950/60 to-ink-900 p-3.5">
          <div className="pointer-events-none absolute -right-6 -top-8 h-20 w-20 rounded-full bg-brand-500/25 blur-2xl"></div>
          <p className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.14em] text-brand-300">
            <Icon name="zap" className="h-3 w-3 text-emerald-400" /> Oportunidades Menores
          </p>
          <p className="mt-2 text-xs leading-relaxed text-ink-200">
            Procesos directos de hasta <span className="font-bold text-white">S/ 42,800</span> con cotización rápida.
          </p>
          <NavLink
            to="/menores"
            className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-emerald-300 transition-colors hover:text-emerald-200"
          >
            Explorar menores <Icon name="arrow-right" className="h-3 w-3" />
          </NavLink>
        </div>

        {user ? (
          <div className="flex items-center gap-2.5 rounded-xl border border-white/5 bg-white/[0.03] p-2.5">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-gradient-to-br from-brand-500 to-fuchsia-500 text-[11px] font-bold text-white uppercase">
              {user.nombre ? user.nombre.slice(0, 2) : 'US'}
            </span>
            <div className="min-w-0 flex-1 leading-tight">
              <p className="truncate text-[13px] font-bold text-white">{user.nombre}</p>
              <p className="truncate text-[10px] text-ink-400 capitalize">{user.rol} · {user.email}</p>
            </div>
            <button
              onClick={logout}
              className="icon-btn-dark hover:text-red-400"
              title="Cerrar sesión"
            >
              <Icon name="log-out" className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => openAuthModal('login')}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-3 py-2 text-xs font-bold text-white shadow-md hover:bg-brand-500 transition-colors"
          >
            <Icon name="user" className="h-4 w-4" />
            Iniciar Sesión
          </button>
        )}
      </div>
    </aside>
  )
}
