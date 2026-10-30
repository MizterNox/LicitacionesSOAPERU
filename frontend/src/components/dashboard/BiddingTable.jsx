// Data table de convocatorias — conectada dinámicamente con PostgreSQL vía FastAPI.
// Responsive: Modo tarjetas táctiles en dispositivos móviles (< md) y tabla densa en escritorio (>= md).

import { useApp } from '../../store/AppState.jsx'
import { Icon } from '../ui/Icon.jsx'
import { ScoreCell, ScoreRing, TypeBadge, StatusBadge, TipoObjetoBadge, RubroBadge, SoaPeruTagBadge } from './badges.jsx'
import { ExportMenu } from './ExportMenu.jsx'
import { fmtPEN, fmtDateShort, daysUntil } from '../../utils/format.js'
import { TableRowSkeleton, MobileCardSkeleton } from '../ui/Skeleton.jsx'

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

/** Fila para vista de escritorio */
function DesktopRow({ c, selected, onSelect }) {
  return (
    <tr
      onClick={onSelect}
      className={`group cursor-pointer border-b border-slate-100 transition-colors last:border-0 ${
        selected ? 'bg-brand-50/60' : 'hover:bg-slate-50/80'
      }`}
    >
      <td className="px-4 py-3">
        <ScoreCell p={c.relevance_score ?? c.match_score ?? 0} primaryTag={c.primary_tag} />
      </td>
      <td className="px-3 py-3">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="font-mono text-xs font-bold tracking-tight text-slate-700">{c.codigo_seace}</span>
          <TypeBadge tipo={c.tipo_proceso} />
          {c.primary_tag && <SoaPeruTagBadge tag={c.primary_tag} />}
          {(c.is_minor_contract || c.es_menor_cuantia) && (
            <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-bold text-emerald-700 border border-emerald-200" title="Contratación Menor a 8 UIT">
              <Icon name="zap" className="h-2.5 w-2.5 text-emerald-600" /> ≤ 8 UIT
            </span>
          )}
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
        <p className="line-clamp-2 max-w-[420px] text-[13px] leading-snug text-slate-700">{c.objeto}</p>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <TipoObjetoBadge tipo={c.tipo_objeto} />
          {c.rubro && <RubroBadge rubro={c.rubro} />}
          {c.matched_keywords && c.matched_keywords.slice(0, 2).map((kw) => (
            <span key={kw} className="rounded bg-indigo-50 px-1.5 py-0.5 text-[9px] font-bold text-indigo-700 border border-indigo-200">
              #{kw}
            </span>
          ))}
          {c.cui && (
            <span className="font-mono text-[10px] font-semibold text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
              CUI {c.cui}
            </span>
          )}
          {c.items && c.items.length > 0 && (
            <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
              {c.items.length} {c.items.length === 1 ? 'ítem' : 'ítems'}
            </span>
          )}
        </div>
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

/** Tarjeta optimizada para pantallas móviles (< md) */
function MobileCard({ c, selected, onSelect }) {
  return (
    <article
      onClick={onSelect}
      className={`p-3.5 transition-all cursor-pointer active:scale-[0.99] border-b border-slate-100 last:border-0 ${
        selected ? 'bg-brand-50/70 ring-1 ring-inset ring-brand-500/20' : 'hover:bg-slate-50/80'
      }`}
    >
      {/* Cabecera: Score + Código + Tipo + Estado */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0 flex-wrap">
          <ScoreRing p={c.relevance_score ?? c.match_score ?? 0} primaryTag={c.primary_tag} className="h-7 w-7 flex-shrink-0" />
          <span className="font-mono text-xs font-bold text-slate-800 truncate">{c.codigo_seace}</span>
          <TypeBadge tipo={c.tipo_proceso} />
          {c.primary_tag && <SoaPeruTagBadge tag={c.primary_tag} />}
          {(c.is_minor_contract || c.es_menor_cuantia) && (
            <span className="inline-flex items-center gap-0.5 rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-bold text-emerald-700 border border-emerald-200">
              <Icon name="zap" className="h-2.5 w-2.5 text-emerald-600" /> ≤ 8 UIT
            </span>
          )}
        </div>
        <StatusBadge estado={c.estado} />
      </div>

      {/* Entidad y Región */}
      <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
        <span className="font-semibold text-slate-700 truncate max-w-[210px]">{c.entidad}</span>
        <span className="flex items-center gap-1 text-[11px] text-slate-400 flex-shrink-0">
          <Icon name="map-pin" className="h-3 w-3" />
          {c.region}
        </span>
      </div>

      {/* Objeto de contratación */}
      <p className="mt-1.5 text-xs text-slate-700 leading-snug line-clamp-2">
        {c.objeto}
      </p>

      {/* Badges de Rubro IA y Tipo */}
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <TipoObjetoBadge tipo={c.tipo_objeto} />
        {c.rubro && <RubroBadge rubro={c.rubro} />}
        {c.cui && (
          <span className="font-mono text-[10px] font-semibold text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
            CUI {c.cui}
          </span>
        )}
        {c.items && c.items.length > 0 && (
          <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
            {c.items.length} {c.items.length === 1 ? 'ítem' : 'ítems'}
          </span>
        )}
      </div>

      {/* Fila inferior: Valor y Plazo */}
      <div className="mt-2.5 flex items-center justify-between border-t border-slate-100 pt-2 text-xs">
        <div>
          <span className="text-[10px] uppercase font-bold text-slate-400 block leading-tight">Valor est.</span>
          <span className="font-bold text-slate-900 tabular-nums">
            {c.valor_estimado != null ? fmtPEN(c.valor_estimado) : 'N/D'}
          </span>
        </div>
        <div className="text-right flex items-center gap-2">
          <DeadlineCell c={c} />
          <Icon name="chevron-right" className="h-4 w-4 text-slate-300" />
        </div>
      </div>
    </article>
  )
}

export default function BiddingTable({ rows }) {
  const { state, dispatch } = useApp()
  const totalCount = state.convocatorias?.length || 0

  return (
    <section className="card overflow-hidden" aria-label="Resultados de convocatorias">
      {/* Toolbar superior */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-slate-200 px-3.5 py-2.5 sm:px-4 sm:py-3">
        <div className="flex items-center gap-1.5 text-xs sm:text-[13px] text-slate-500">
          <span className="font-bold text-slate-900">Resultados</span>
          <span className="rounded-md bg-brand-50 px-1.5 py-0.5 text-xs font-bold text-brand-700">{rows.length}</span>
          <span className="hidden sm:inline">convocatorias disponibles</span>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <div className="relative">
            <select
              value={state.sort}
              onChange={(e) => dispatch({ type: 'SET_SORT', sort: e.target.value })}
              className="field h-8 w-auto appearance-none rounded-lg pr-7 text-xs"
              title="Ordenar resultados"
            >
              <option value="date">Más recientes</option>
              <option value="match">Relevancia IA</option>
              <option value="value">Valor estimado</option>
              <option value="deadline">Plazo más corto</option>
            </select>
            <Icon name="chevron-down" className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          </div>
          <ExportMenu />
        </div>
      </div>

      {/* Vista Móvil: Tarjetas táctiles (< md) */}
      <div className="md:hidden">
        {state.isLoading ? (
          <div className="divide-y divide-slate-100">
            <MobileCardSkeleton />
            <MobileCardSkeleton />
            <MobileCardSkeleton />
            <MobileCardSkeleton />
          </div>
        ) : rows.length ? (
          <div className="divide-y divide-slate-100">
            {rows.map((c) => (
              <MobileCard
                key={c.id}
                c={c}
                selected={c.id === state.selectedId}
                onSelect={() => dispatch({ type: 'SELECT_BID', id: c.id })}
              />
            ))}
          </div>
        ) : (
          <div className="px-6 py-12 text-center">
            <span className="mx-auto grid h-10 w-10 place-items-center rounded-full bg-slate-100 text-slate-400">
              <Icon name="search" className="h-5 w-5" />
            </span>
            <p className="mt-3 text-xs font-semibold text-slate-700">Sin resultados encontrados</p>
            <button
              onClick={() => dispatch({ type: 'CLEAR_FILTERS' })}
              className="btn-ghost mt-2 h-7 px-2.5 text-xs"
            >
              Limpiar filtros
            </button>
          </div>
        )}
      </div>

      {/* Vista Desktop: Tabla completa densa (>= md) */}
      <div className="hidden md:block overflow-x-auto scroll-thin">
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
              <>
                <TableRowSkeleton />
                <TableRowSkeleton />
                <TableRowSkeleton />
                <TableRowSkeleton />
                <TableRowSkeleton />
              </>
            ) : rows.length ? (
              rows.map((c) => (
                <DesktopRow
                  key={c.id}
                  c={c}
                  selected={c.id === state.selectedId}
                  onSelect={() => dispatch({ type: 'SELECT_BID', id: c.id })}
                />
              ))
            ) : (
              <tr>
                <td colSpan={8} className="px-6 py-14 text-center">
                  <div className="mx-auto flex max-w-xs flex-col items-center">
                    <span className="grid h-11 w-11 place-items-center rounded-full bg-slate-100 text-slate-400">
                      <Icon name="search" className="h-5 w-5" />
                    </span>
                    <p className="mt-3 text-sm font-semibold text-slate-700">Sin resultados encontrados</p>
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
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 bg-slate-50/50 px-3.5 py-2 sm:px-4 sm:py-2.5 text-xs text-slate-500">
        <span>
          Mostrando <span className="font-semibold text-slate-700">{rows.length}</span> de{' '}
          <span className="font-semibold text-slate-700">{totalCount}</span> convocatorias
        </span>
      </div>
    </section>
  )
}
