// ProtectedRoute: guarda de rutas privadas para React Router.
// - Mientras se verifica la sesión muestra un estado de carga (evita parpadeos de UI).
// - Sin sesión, mantiene la URL y muestra un panel de acceso restringido con login;
//   al autenticarse, el contenido protegido se renderiza sin perder la ruta solicitada.

import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../store/AuthContext.jsx'
import { Icon } from '../ui/Icon.jsx'

export default function ProtectedRoute({ children, autoOpenLogin = true }) {
  const { isAuthenticated, isLoading, openAuthModal } = useAuth()
  const location = useLocation()

  useEffect(() => {
    if (!isLoading && !isAuthenticated && autoOpenLogin) openAuthModal('login')
    // Solo al entrar a la ruta o cuando cambia el estado de sesión
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, isAuthenticated, location.pathname])

  if (isLoading) {
    return (
      <div className="flex h-full min-h-[50vh] items-center justify-center" role="status" aria-live="polite">
        <span className="h-6 w-6 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
        <span className="sr-only">Verificando sesión…</span>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="flex h-full min-h-[60vh] items-center justify-center p-6">
        <div className="card max-w-md p-8 text-center">
          <span className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-slate-100 text-slate-500">
            <Icon name="lock" className="h-6 w-6" />
          </span>
          <h2 className="mt-4 text-lg font-bold text-slate-900">Acceso restringido</h2>
          <p className="mt-2 text-sm text-slate-500">
            Esta sección requiere una sesión activa. Inicia sesión con tu cuenta para continuar.
          </p>
          <button type="button" onClick={() => openAuthModal('login')} className="btn-primary mt-6 justify-center">
            Iniciar sesión
          </button>
        </div>
      </div>
    )
  }

  return children ?? <Outlet />
}
