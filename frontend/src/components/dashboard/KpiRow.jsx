// Fila de KPIs — todas las métricas se calculan dinámicamente desde state.convocatorias (PostgreSQL).

import { useApp } from '../../store/AppState.jsx'
import { Icon } from '../ui/Icon.jsx'
import { TODAY, parseISO, daysUntil } from '../../utils/format.js'

export default function KpiRow() {
  const { state } = useApp()
  const convocatorias = state.convocatorias || []

  const VIGENTES = convocatorias.filter((c) => c.estado === 'Vigente')
  const NUEVAS_7D = convocatorias.filter((c) => {
    if (!c.fecha_publicacion) return false
    const d = Math.round((TODAY - parseISO(c.fecha_publicacion)) / 86400000)
    return d >= 0 && d <= 7
  }).length

  const SUGERIDAS = VIGENTES.filter((c) => (c.relevance_score ?? c.match_score ?? 0) >= 40).length
  const ALTA_RELEVANCIA = VIGENTES.filter((c) => (c.relevance_score ?? 0) >= 75).length
  const CIERRES_48H = VIGENTES.filter((c) => {
    const dl = c.fecha_limite ? daysUntil(c.fecha_limite) : null
    return dl != null && dl >= 0 && dl <= 2
  }).length

  const MONTO = VIGENTES.reduce((acc, c) => acc + (c.valor_estimado ?? 0), 0)
  const MOUNT = MONTO >= 1e6
    ? `S/ ${(MONTO / 1e6).toFixed(1).replace('.', ',')}M`
    : `S/ ${(MONTO / 1e3).toFixed(1).replace('.', ',')}K`

  const KPIS = [
    {
      label: 'Convocatorias activas (en BD)',
      value: String(VIGENTES.length),
      delta: `${convocatorias.length} totales registradas`,
      deltaCls: 'text-emerald-600',
      deltaIcon: 'trending-up',
      icon: 'inbox',
      iconCls: 'bg-emerald-50 text-emerald-600',
      dark: false,
    },
    {
      label: 'Oportunidades SOAPERU TI',
      value: String(SUGERIDAS),
      delta: `${ALTA_RELEVANCIA} de alta afinidad (≥75 pts)`,
      deltaCls: 'text-emerald-300',
      deltaIcon: 'sparkles',
      icon: 'sparkles',
      iconCls: 'bg-brand-500/20 text-brand-300',
      dark: true,
    },
    {
      label: 'Próximos cierres (48 h)',
      value: String(CIERRES_48H),
      delta: 'requieren acción inmediata',
      deltaCls: 'text-amber-600',
      deltaIcon: 'alert-triangle',
      icon: 'hourglass',
      iconCls: 'bg-amber-50 text-amber-600',
      dark: false,
    },
    {
      label: 'Monto total en juego (S/)',
      value: MOUNT,
      delta: 'solo procesos Vigentes',
      deltaCls: 'text-emerald-600',
      deltaIcon: 'trending-up',
      icon: 'banknote',
      iconCls: 'bg-slate-100 text-slate-500',
      dark: false,
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {KPIS.map((k) => (
        <article
          key={k.label}
          className={k.dark ? 'relative overflow-hidden rounded-xl border border-ink-800 bg-ink-950 p-4 shadow-card sm:p-5' : 'card p-4 sm:p-5'}
        >
          {k.dark && <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-brand-500/25 blur-2xl"></div>}
          <div className="flex items-start justify-between gap-2">
            <p className={`text-[13px] font-medium ${k.dark ? 'text-ink-300' : 'text-slate-500'}`}>{k.label}</p>
            <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg ${k.iconCls}`}>
              <Icon name={k.icon} className="h-4 w-4" />
            </span>
          </div>
          <p className={`mt-2.5 text-[26px] font-extrabold leading-none tracking-tight tabular-nums ${k.dark ? 'text-white' : 'text-slate-900'}`}>
            {k.value}
          </p>
          <p className={`mt-2.5 flex items-center gap-1 text-[11px] font-semibold ${k.deltaCls}`}>
            <Icon name={k.deltaIcon} className="h-3.5 w-3.5" />
            {k.delta}
          </p>
        </article>
      ))}
    </div>
  )
}
