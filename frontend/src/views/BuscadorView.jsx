// Vista del Buscador SEACE: Búsqueda avanzada y análisis multicriterio.

import { useApp } from '../store/AppState.jsx'
import { useSelectedConvocatoria, useVisibleConvocatorias } from '../store/selectors.js'
import FilterBar from '../components/dashboard/FilterBar.jsx'
import BiddingTable from '../components/dashboard/BiddingTable.jsx'
import DetailPanel from '../components/dashboard/DetailPanel.jsx'
import { Icon } from '../components/ui/Icon.jsx'

export default function BuscadorView() {
  const { state, dispatch } = useApp()
  const rows = useVisibleConvocatorias()
  const selected = useSelectedConvocatoria()

  return (
    <div className="flex h-full min-h-0">
      <div className="mx-auto max-w-[1560px] min-w-0 flex-1 space-y-4 p-4 md:space-y-5 md:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-200 pb-3">
          <div>
            <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Icon name="search" className="h-5 w-5 text-brand-600" />
              Buscador Avanzado SEACE
            </h1>
            <p className="text-xs text-slate-500">
              Exploración de convocatorias del Estado con filtros por tipo de objeto, rubro IA, entidades y regiones.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500">
              {rows.length} convocatorias encontradas
            </span>
          </div>
        </div>

        <FilterBar />
        <BiddingTable rows={rows} />
      </div>

      {selected && (
        <>
          <div
            className="fixed inset-0 z-40 bg-slate-950/40 backdrop-blur-[2px] xl:hidden"
            onClick={() => dispatch({ type: 'CLOSE_DETAIL' })}
          />
          <DetailPanel bid={selected} />
        </>
      )}
    </div>
  )
}
