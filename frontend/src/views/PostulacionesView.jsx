// Vista de Mis Postulaciones (Pipeline / Kanban de seguimiento).

import { Link } from 'react-router-dom'
import { Icon } from '../components/ui/Icon.jsx'

export default function PostulacionesView() {
  return (
    <div className="mx-auto max-w-[1560px] p-4 md:p-6">
      <div className="card grid min-h-[60vh] place-items-center p-10 text-center">
        <div className="max-w-md space-y-4">
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-brand-50 text-brand-600">
            <Icon name="kanban" className="h-6 w-6" />
          </span>
          <h1 className="text-xl font-bold text-slate-900">Mis Postulaciones</h1>
          <p className="text-sm leading-relaxed text-slate-500">
            Pipeline de seguimiento de tus ofertas presentadas ante entidades del Estado: cotizaciones en curso, calificación técnica, subsanaciones y otorgamiento de la Buena Pro.
          </p>
          <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-800 border border-emerald-200">
            <Icon name="zap" className="h-3.5 w-3.5 text-emerald-600" /> Compatible con cotizaciones de menor cuantía
          </div>
          <div className="pt-2">
            <Link to="/menores" className="btn-primary inline-flex items-center gap-1.5">
              <Icon name="search" className="h-4 w-4" /> Explorar Contrataciones Menores
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
