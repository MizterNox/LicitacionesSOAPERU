// AppLayout: Layout maestro estructurado con React Router.
// Sidebar fija/colapsable + Header Topbar + Franja de Urgencias + <Outlet />

import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { useApp } from '../../store/AppState.jsx'
import Sidebar from './Sidebar.jsx'
import Topbar, { UrgentStrip } from './Topbar.jsx'
import AuthModal from '../auth/AuthModal.jsx'

export default function AppLayout() {
  const { state, dispatch } = useApp()

  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== 'Escape') return
      if (state.mobileNavOpen) dispatch({ type: 'CLOSE_MOBILE_NAV' })
      else if (state.selectedId != null) dispatch({ type: 'CLOSE_DETAIL' })
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [state.mobileNavOpen, state.selectedId, dispatch])

  return (
    <div className="flex h-full min-h-0 bg-slate-100/60 antialiased">
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
        <main className="flex min-h-0 flex-1 overflow-hidden">
          <section className="scroll-thin min-w-0 flex-1 overflow-y-auto">
            <Outlet />
          </section>
        </main>
      </div>
      <AuthModal />
    </div>
  )
}
