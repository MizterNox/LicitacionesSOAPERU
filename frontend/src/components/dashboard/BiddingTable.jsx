// Data table de convocatorias — conectada dinámicamente con PostgreSQL vía FastAPI.

import { useApp } from '../../store/AppState.jsx'
import { Icon } from '../ui/Icon.jsx'
import { ScoreCell, TypeBadge, StatusBadge, TipoObjetoBadge } from './badges.jsx'
import { fmtPEN, fmtDateShort, daysUntil } from '../../utils/format.js'

function DeadlineCell({ c }) {
  if (c.estado !== 'Vigente' || !c.fecha_limite) return <span className="text-xs text-slate-300">—</span>
  const d = daysUntil(c.fecha_limite)
  if (d < 0) {
    return (
      <div>
        <div className="text-[13px] font-medium tabular-nums text-slate-400">{fmtDateShort(c.fecha_limite)}</div>
        <div className="text-[11px] font-medium text-slate-400">Vencido</div>
      </div>
    )
  }
  const tone = d <= 2 ? 'text-red-600' : d <= 4 ? 'text-amber-600' : 'text-slate-600'
  const sub = d <= 1 ? '≤ 24 h' : `${d} días`
  return (
    <div>
      <div className={`text-[13px] font-bold tabular-nums ${tone}`}>{fmtDateShort(c.fecha_limite)}</div>
      <div className={`flex items-center gap-1 text-[11px] font-medium ${tone} opacity-80`}>
        {d <= 2 ? <Icon name="clock" className="h-3 w-3" /> : null}
        {sub}
      </div>
    </div>
  )
}

function Row({ c, selected, onSelect }) {
  return (
    <tr onClick={onSelect} className={`group cursor-pointer border-b border-slate-100 transition-colors last:border-0 ${selected ? 'bg-brand-50/60' : 'hover:bg-slate-50/80'}`}>
      <td className="px-4 py-3">
        <ScoreCell p={c.match_score} />
      </td>
      <td className="px-3 py-3">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-xs font-bold tracking-tight text-slate-700">{c.codigo_seace}</span>
          <TypeBadge tipo={c.tipo_proceso} />
        </div>
      </td>
      <td className="px-3 py-3">
        <div className="max-w-[170px] truncate text-[13px] font-semibold text-slate-700">{c.entidad}</div>
        <div className="mt-0.5 flex items-center gap-1 text-[11px] text-slate-400">
          <Icon name="map-pin" className="h-3 w-3" />
          {c.region}
        </div>
      </td>
      <td className="px-3 py-3">
        <p className="line-clamp-2 max-w-[420px] text-[13px] leading-snug text-slate-600">{c.objeto}</p>
        <TipoObjetoBadge tipo={c.tipo_objeto} />
      </td>
      <td className="px-3 py-3 text-right">
        {c.valor_estimado != null ? (
          <span className="text-[13px] font-bold tabular-nums text-slate-800">{fmtPEN(c.valor_estimado)}</span>
        ) : (
          <span className="text-xs text-slate-400">N/D</span>
        )}
      </td>
      <td className="px-3 py-3">
        <StatusBadge estado={c.estado} />
      </td>
      <td className="px-3 py-3">
        <DeadlineCell c={c} />
      </td>
      <td className="px-3 py-3 text-right">
        <span className="inline-flex h-7 w-7 items-center justify-center rounded-md text-slate-400 opacity-0 transition-opacity group-hover:opacity-100">
          <Icon name="chevron-right" className="h-4 w-4" />
        </span>
      </td>
    </tr>
  )
}

export default function BiddingTable({ rows }) {
  const { state, dispatch } = useApp()
  const totalCount = state.convocatorias?.length || 0

  return (
    <section className="card overflow-hidden" aria-label="Resultados de convocatorias">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-slate-200 px-4 py-3">
        <div className="flex items-center gap-2 text-[13px] text-slate-500">
          <span className="font-bold text-slate-900">Resultados</span>
          <span className="rounded-md bg-brand-50 px-1.5 py-0.5 text-xs font-bold text-brand-700">{rows.length}</span>
          <span className="hidden text-xs sm:inline">convocatorias desde PostgreSQL</span>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <div className="relative">
            <select
              value={state.sort}
              onChange={(e) => dispatch({ type: 'SET_SORT', sort: e.target.value })}
              className="field h-8 w-auto appearance-none rounded-lg pr-7 text-xs"
              title="Ordenar resultados"
            >
              <option value="date">Ordenar: Más recientes primero</option>
              <option value="match">Ordenar: Relevancia IA</option>
              <option value="value">Ordenar: Valor estimado</option>
              <option value="deadline">Ordenar: Plazo más corto</option>
            </select>
            <Icon name="chevron-down" className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          </div>
          <button className="icon-btn h-8 w-8" title="Exportar resultados">
            <Icon name="download" className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Tabla */}
      <div className="overflow-x-auto scroll-thin">
        <table className="w-full min-w-[860px] border-collapse text-left">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50/80">
              <th className="w-[84px] px-4 py-2.5">
                <span className="flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  <Icon name="sparkles" className="h-3 w-3 text-brand-500" /> Match IA
                </span>
              </th>
              <th className="w-[190px] px-3 py-2.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">Convocatoria</th>
              <th className="w-[190px] px-3 py-2.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">Entidad</th>
              <th className="px-3 py-2.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">Objeto de contratación</th>
              <th className="w-[124px] px-3 py-2.5 text-right text-[11px] font-bold uppercase tracking-wider text-slate-400">Valor est.</th>
              <th className="w-[130px] px-3 py-2.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">Estado</th>
              <th className="w-[100px] px-3 py-2.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">Plazo</th>
              <th className="w-[52px] px-3 py-2.5"></th>
            </tr>
          </thead>
          <tbody>
            {state.isLoading ? (
              <tr>
                <td colSpan={8} className="px-6 py-12 text-center text-slate-400">
                  <div className="flex flex-col items-center gap-2">
                    <span className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
                    <p className="text-xs font-semibold text-slate-500">Consultando base de datos PostgreSQL...</p>
                  </div>
                </td>
              </tr>
            ) : rows.length ? (
              rows.map((c) => (
                <Row key={c.id} c={c} selected={c.id === state.selectedId} onSelect={() => dispatch({ type: 'SELECT_BID', id: c.id })} />
              ))
            ) : (
              <tr>
                <td colSpan={8} className="px-6 py-14 text-center">
                  <div className="mx-auto flex max-w-xs flex-col items-center">
                    <span className="grid h-11 w-11 place-items-center rounded-full bg-slate-100 text-slate-400">
                      <Icon name="search" className="h-5 w-5" />
                    </span>
                    <p className="mt-3 text-sm font-semibold text-slate-700">Sin resultados en PostgreSQL</p>
                    <p className="mt-1 text-xs text-slate-400">Ninguna convocatoria coincide con los filtros seleccionados.</p>
                    <button onClick={() => dispatch({ type: 'CLEAR_FILTERS' })} className="btn-ghost mt-3 h-8 px-3 text-xs">
                      Limpiar filtros
                    </button>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 bg-slate-50/50 px-4 py-2.5 text-xs text-slate-500">
        <span>
          Mostrando <span className="font-semibold text-slate-700">{rows.length}</span> de{' '}
          <span className="font-semibold text-slate-700">{totalCount}</span> convocatorias cargadas
        </span>
      </div>
    </section>
  )
}
