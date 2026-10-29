import { fmtPEN } from '../../utils/format.js'
import { Icon } from '../ui/Icon.jsx'

export function TopEntitiesTable({ entidades }) {
  const maxMonto = Math.max(...(entidades || []).map((e) => e.monto), 1)

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-sky-50 text-sky-600">
            <Icon name="building-2" className="h-4 w-4" />
          </span>
          <div>
            <h3 className="text-sm font-bold text-slate-900">Entidades con Mayor Presupuesto</h3>
            <p className="text-xs text-slate-500">Compradores públicos más activos por volumen contratado</p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {(entidades || []).map((ent, idx) => {
          const ratio = Math.min(Math.round((ent.monto / maxMonto) * 100), 100)
          return (
            <div key={ent.entidad} className="group rounded-lg p-2 hover:bg-slate-50/80 transition-colors">
              <div className="flex items-center justify-between text-xs mb-1.5">
                <div className="flex items-center gap-2 min-w-0 pr-2">
                  <span className="grid h-5 w-5 flex-shrink-0 place-items-center rounded-md bg-slate-100 text-[10px] font-bold text-slate-600">
                    {idx + 1}
                  </span>
                  <span className="font-semibold text-slate-800 truncate" title={ent.entidad}>
                    {ent.entidad}
                  </span>
                </div>
                <div className="text-right flex-shrink-0">
                  <span className="font-bold text-slate-900 tabular-nums">{fmtPEN(ent.monto)}</span>
                  <span className="text-[11px] text-slate-400 ml-1.5">({ent.count} proc.)</span>
                </div>
              </div>
              {/* Barra de progreso visual */}
              <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-sky-500 to-brand-500 transition-all duration-500"
                  style={{ width: `${ratio}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
