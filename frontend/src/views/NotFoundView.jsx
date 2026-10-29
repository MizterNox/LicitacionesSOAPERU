// Vista 404: Página no encontrada con diseño corporativo.

import { Link } from 'react-router-dom'
import { Icon } from '../components/ui/Icon.jsx'

export default function NotFoundView() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-4">
      <div className="card max-w-md p-8 text-center space-y-4 shadow-sm border border-slate-200">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-brand-50 text-brand-600">
          <Icon name="search" className="h-7 w-7" />
        </span>
        <h1 className="text-xl font-bold text-slate-900">Página no encontrada (404)</h1>
        <p className="text-xs text-slate-500 leading-relaxed">
          La ruta solicitada no existe o fue movida. Puedes volver al centro de mando para continuar explorando oportunidades.
        </p>
        <div className="pt-2">
          <Link to="/dashboard" className="btn-primary inline-flex items-center gap-1.5">
            <Icon name="layout-dashboard" className="h-4 w-4" /> Volver al Dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}
