// Vista especializada: Contrataciones Menores (<= 8 UIT)
// Centro ágil de cotizaciones directas y detección temprana de oportunidades del Estado.

import { useEffect, useMemo } from 'react'
import { useApp } from '../store/AppState.jsx'
import { useSelectedConvocatoria } from '../store/selectors.js'
import FilterBar from '../components/dashboard/FilterBar.jsx'
import BiddingTable from '../components/dashboard/BiddingTable.jsx'
import DetailPanel from '../components/dashboard/DetailPanel.jsx'
import { Icon } from '../components/ui/Icon.jsx'
import { fmtPEN, daysUntil } from '../utils/format.js'

export default function MinorProcurementView() {
  const { state, dispatch } = useApp()
  const selected = useSelectedConvocatoria()

  // Forzar filtro de solo menores al ingresar
  useEffect(() => {
    if (!state.filters.soloMenores) {
      dispatch({ type: 'SET_FILTER', key: 'soloMenores', value: true })
    }
  }, [state.filters.soloMenores, dispatch])

  // Filtrado de menores
  const menoresRows = useMemo(() => {
    const list = state.convocatorias || []
    return list.filter((c) => c.es_menor_cuantia)
  }, [state.convocatorias])

  // Métricas específicas del nicho de contrataciones menores
  const stats = useMemo(() => {
    const total = menoresRows.length
    const urgentes48h = menoresRows.filter((c) => {
      if (!c.fecha_limite) return false
      const d = daysUntil(c.fecha_limite)
      return d >= 0 && d <= 2
    }).length

    const sumaMontos = menoresRows.reduce((acc, c) => acc + (c.valor_estimado || 0), 0)
    const promedio = total > 0 ? sumaMontos / total : 0
    const entidadesSet = new Set(menoresRows.map((c) => c.entidad).filter(Boolean))

    return {
      total,
      urgentes48h,
      promedio,
      entidadesCount: entidadesSet.size,
    }
  }, [menoresRows])

  return (
    <div className="flex h-full min-h-0">
      <div className="mx-auto max-w-[1560px] min-w-0 flex-1 space-y-4 p-4 md:space-y-5 md:p-6">
        {/* Banner Hero Especializado en Menor Cuantía */}
        <div className="relative overflow-hidden rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-emerald-950 via-ink-950 to-slate-900 p-5 text-white shadow-lg">
          <div className="pointer-events-none absolute -right-12 -top-12 h-44 w-44 rounded-full bg-emerald-500/15 blur-3xl" />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-[11px] font-bold text-emerald-300 border border-emerald-500/30">
                  <Icon name="zap" className="h-3 w-3" /> Nicho Estratégico · Sector Público
                </span>
                <span className="text-[11px] font-semibold text-slate-400">
                  Tope: ≤ 8 UIT (S/ 42,800 PEN)
                </span>
              </div>
              <h1 className="text-xl font-extrabold tracking-tight sm:text-2xl">
                Oportunidades de Contratación Menor
              </h1>
              <p className="max-w-2xl text-xs text-slate-300 leading-relaxed sm:text-sm">
                Procesos ágiles con plazos de cotización electrónica breves (48 h a 5 días). Diseñado para adjudicación rápida y baja fricción operativa.
              </p>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              <button
                type="button"
                onClick={() => dispatch({ type: 'SET_FILTER', key: 'plazo', value: '48h' })}
                className="inline-flex items-center gap-1.5 rounded-xl border border-red-500/30 bg-red-500/20 px-3 py-2 text-xs font-bold text-red-200 transition-colors hover:bg-red-500/30 shadow-xs"
              >
                <Icon name="clock" className="h-4 w-4 text-red-400" />
                <span>Ver cierres en ≤ 48 h</span>
              </button>
            </div>
          </div>

          {/* Tarjetas KPI del Nicho */}
          <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4 border-t border-white/10 pt-4">
            <div className="bg-white/5 rounded-xl p-3 border border-white/5">
              <span className="text-[11px] font-medium text-emerald-300">Oportunidades Menores</span>
              <p className="mt-1 text-lg font-bold text-white tabular-nums">{stats.total}</p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 border border-white/5">
              <span className="text-[11px] font-medium text-red-300">Cierre Inmediato (≤ 48 h)</span>
              <p className="mt-1 text-lg font-bold text-red-400 tabular-nums">{stats.urgentes48h}</p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 border border-white/5">
              <span className="text-[11px] font-medium text-slate-300">Monto Promedio</span>
              <p className="mt-1 text-lg font-bold text-white tabular-nums">{fmtPEN(stats.promedio)}</p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 border border-white/5">
              <span className="text-[11px] font-medium text-slate-300">Entidades Compradoras</span>
              <p className="mt-1 text-lg font-bold text-white tabular-nums">{stats.entidadesCount}</p>
            </div>
          </div>
        </div>

        {/* Barra de Filtros */}
        <FilterBar />

        {/* Tabla de Convocatorias Menores */}
        <BiddingTable rows={menoresRows} />
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
