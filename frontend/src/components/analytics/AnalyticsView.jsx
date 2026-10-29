import { useState, useEffect } from 'react'
import { tendersApi } from '../../lib/api.js'
import { fmtPEN } from '../../utils/format.js'
import { Icon } from '../ui/Icon.jsx'
import { MonthlyVolumeChart } from './MonthlyVolumeChart.jsx'
import { RubroDonutChart } from './RubroDonutChart.jsx'
import { AmountTrendChart } from './AmountTrendChart.jsx'
import { TopEntitiesTable } from './TopEntitiesTable.jsx'

function MetricKpiCard({ title, value, subtitle, icon, iconColor, bgIcon }) {
  return (
    <div className="card p-4 flex items-center justify-between">
      <div>
        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">{title}</p>
        <p className="text-xl font-extrabold text-slate-900 mt-1 tabular-nums">{value}</p>
        {subtitle && <p className="text-[11px] text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      <span className={`grid h-11 w-11 place-items-center rounded-xl ${bgIcon} ${iconColor}`}>
        <Icon name={icon} className="h-5 w-5" />
      </span>
    </div>
  )
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-5 animate-pulse">
      {/* KPIs Skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="card h-24 bg-slate-100/60 rounded-xl" />
        ))}
      </div>
      {/* Charts Skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="card h-96 lg:col-span-2 bg-slate-100/60 rounded-xl" />
        <div className="card h-96 bg-slate-100/60 rounded-xl" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="card h-80 lg:col-span-2 bg-slate-100/60 rounded-xl" />
        <div className="card h-80 bg-slate-100/60 rounded-xl" />
      </div>
    </div>
  )
}

export function AnalyticsView() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [summary, setSummary] = useState(null)
  const [monthlyData, setMonthlyData] = useState([])
  const [grupos, setGrupos] = useState([])
  const [groupBy, setGroupBy] = useState('tipo') // 'tipo' | 'rubro'
  const [meses, setMeses] = useState(12)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [sumRes, monthRes] = await Promise.all([
        tendersApi.getMetricsSummary(),
        tendersApi.getMonthlyMetrics(meses, groupBy),
      ])
      setSummary(sumRes)
      setMonthlyData(monthRes.data || [])
      setGrupos(monthRes.grupos || [])
    } catch (err) {
      console.error('Error al cargar analítica:', err)
      setError(err.message || 'No se pudieron cargar las métricas')
    } finally {
      setLoading(false)
    }
  }

  // Recargar al cambiar periodo o agrupación
  useEffect(() => {
    loadData()
  }, [meses, groupBy])

  if (loading && !summary) {
    return (
      <div className="mx-auto max-w-[1560px] p-4 md:p-6">
        <AnalyticsSkeleton />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[1560px] space-y-5 p-4 md:p-6">
      {/* Header de la vista */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
            Analítica de Contrataciones Públicas
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Métricas estratégicas consolidadas del SEACE con clasificación inteligente por IA.
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="inline-flex items-center gap-1.5 self-start sm:self-auto rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 transition-colors disabled:opacity-60"
        >
          <Icon name="clock" className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Actualizar métricas
        </button>
      </div>

      {/* Alerta de error si ocurre */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon name="alert-triangle" className="h-4 w-4 flex-shrink-0 text-red-500" />
            <span>{error}</span>
          </div>
          <button onClick={loadData} className="font-bold underline ml-4">
            Reintentar
          </button>
        </div>
      )}

      {/* KPI Cards */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricKpiCard
            title="Convocatorias Analizadas"
            value={summary.total_convocatorias.toLocaleString()}
            subtitle={`${summary.vigentes} actualmente vigentes`}
            icon="file-text"
            iconColor="text-brand-600"
            bgIcon="bg-brand-50"
          />
          <MetricKpiCard
            title="Presupuesto Total"
            value={fmtPEN(summary.monto_total)}
            subtitle="Monto estimado en Soles (PEN)"
            icon="banknote"
            iconColor="text-emerald-600"
            bgIcon="bg-emerald-50"
          />
          <MetricKpiCard
            title="Ticket Promedio"
            value={fmtPEN(summary.ticket_promedio)}
            subtitle="Por proceso de contratación"
            icon="trending-up"
            iconColor="text-sky-600"
            bgIcon="bg-sky-50"
          />
          <MetricKpiCard
            title="Rubros Detectados por IA"
            value={(summary.top_rubros || []).length}
            subtitle={summary.top_rubros?.[0] ? `Líder: ${summary.top_rubros[0].rubro}` : 'Categorías'}
            icon="sparkles"
            iconColor="text-indigo-600"
            bgIcon="bg-indigo-50"
          />
        </div>
      )}

      {/* Fila 1 de gráficos: Gráfico temporal apilado + Dona de Rubros */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <MonthlyVolumeChart
            data={monthlyData}
            grupos={grupos}
            groupBy={groupBy}
            onGroupByChange={setGroupBy}
            meses={meses}
            onMesesChange={setMeses}
          />
        </div>
        <div>
          <RubroDonutChart data={summary?.top_rubros || []} />
        </div>
      </div>

      {/* Fila 2 de gráficos: Tendencia de montos + Ranking de Entidades */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <AmountTrendChart data={monthlyData} />
        </div>
        <div>
          <TopEntitiesTable entidades={summary?.top_entidades || []} />
        </div>
      </div>
    </div>
  )
}
