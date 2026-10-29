// Vista principal: Dashboard de inteligencia y centro de mando de convocatorias.

import { useApp } from '../store/AppState.jsx'
import { useSelectedConvocatoria, useVisibleConvocatorias } from '../store/selectors.js'
import KpiRow from '../components/dashboard/KpiRow.jsx'
import FilterBar from '../components/dashboard/FilterBar.jsx'
import BiddingTable from '../components/dashboard/BiddingTable.jsx'
import DetailPanel from '../components/dashboard/DetailPanel.jsx'

export default function DashboardView() {
  const { state, dispatch } = useApp()
  const rows = useVisibleConvocatorias()
  const selected = useSelectedConvocatoria()

  return (
    <div className="flex h-full min-h-0">
      <div className="mx-auto max-w-[1560px] min-w-0 flex-1 space-y-4 p-4 md:space-y-5 md:p-6">
        <KpiRow />
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
