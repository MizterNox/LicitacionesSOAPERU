import { useState } from 'react'
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { fmtPEN } from '../../utils/format.js'
import { Icon } from '../ui/Icon.jsx'

const RUBRO_COLORS = {
  'Tecnología y Software': '#6366F1',
  'Construcción e Infraestructura': '#F59E0B',
  'Salud y Farmacia': '#F43F5E',
  'Consultoría y Asesoría': '#8B5CF6',
  'Mantenimiento y Limpieza': '#14B8A6',
  'Seguridad y Vigilancia': '#3B82F6',
  'Transporte y Logística': '#06B6D4',
  Alimentos: '#F97316',
  'Educación y Capacitación': '#10B981',
  'Equipamiento y Mobiliario': '#A855F7',
  'Servicios Generales': '#64748B',
  Otros: '#94A3B8',
}

const FALLBACK_COLORS = ['#8B5CF6', '#06B6D4', '#10B981', '#F59E0B', '#EC4899', '#6366F1', '#3B82F6', '#14B8A6']

function DonutTooltip({ active, payload, metric }) {
  if (!active || !payload || !payload.length) return null
  const item = payload[0].payload
  const isMonto = metric === 'monto'

  return (
    <div className="rounded-xl border border-slate-200/80 bg-white/95 p-3 shadow-xl backdrop-blur-md text-xs">
      <div className="flex items-center gap-1.5 font-bold text-slate-800">
        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: payload[0].color }} />
        <span>{item.rubro}</span>
      </div>
      <div className="mt-2 space-y-1 text-slate-600">
        <p className="flex justify-between gap-4">
          <span>Convocatorias:</span>
          <span className="font-bold text-slate-900 tabular-nums">{item.count} ({item.porcentaje}%)</span>
        </p>
        <p className="flex justify-between gap-4">
          <span>Presupuesto:</span>
          <span className="font-bold text-slate-900 tabular-nums">{fmtPEN(item.monto)}</span>
        </p>
      </div>
    </div>
  )
}

export function RubroDonutChart({ data }) {
  const [metric, setMetric] = useState('count') // 'count' | 'monto'

  const totalSum = (data || []).reduce(
    (acc, item) => acc + (metric === 'count' ? item.count : item.monto),
    0
  )

  const chartData = (data || []).map((item, idx) => ({
    ...item,
    value: metric === 'count' ? item.count : item.monto,
    fill: RUBRO_COLORS[item.rubro] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length],
  }))

  return (
    <div className="card p-5 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-indigo-50 text-indigo-600">
              <Icon name="tag" className="h-4 w-4" />
            </span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Distribución por Rubro IA</h3>
              <p className="text-[11px] text-slate-500">Clasificación automática de oportunidades</p>
            </div>
          </div>

          {/* Toggle Cantidad vs Monto */}
          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100/80 p-0.5 text-xs">
            <button
              onClick={() => setMetric('count')}
              className={`rounded-md px-2 py-0.5 text-[11px] font-semibold transition-all ${
                metric === 'count' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              N°
            </button>
            <button
              onClick={() => setMetric('monto')}
              className={`rounded-md px-2 py-0.5 text-[11px] font-semibold transition-all ${
                metric === 'monto' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              S/
            </button>
          </div>
        </div>

        {/* Gráfico de dona */}
        <div className="relative h-[210px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={82}
                paddingAngle={3}
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} stroke="white" strokeWidth={2} />
                ))}
              </Pie>
              <Tooltip content={<DonutTooltip metric={metric} />} />
            </PieChart>
          </ResponsiveContainer>

          {/* Centro de la dona */}
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              {metric === 'count' ? 'Total Procesos' : 'Monto Total'}
            </span>
            <span className="text-sm font-black text-slate-900 tabular-nums">
              {metric === 'count' ? totalSum : fmtPEN(totalSum)}
            </span>
          </div>
        </div>
      </div>

      {/* Lista de leyenda compacta */}
      <div className="mt-3 max-h-[160px] overflow-y-auto scroll-thin divide-y divide-slate-100 pr-1">
        {chartData.slice(0, 7).map((item) => (
          <div key={item.rubro} className="flex items-center justify-between py-1.5 text-xs">
            <div className="flex items-center gap-2 min-w-0 pr-2">
              <span
                className="h-2 w-2 flex-shrink-0 rounded-full"
                style={{ backgroundColor: item.fill }}
              />
              <span className="truncate text-slate-700 font-medium" title={item.rubro}>
                {item.rubro}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0 tabular-nums">
              <span className="font-bold text-slate-800">
                {metric === 'count' ? item.count : fmtPEN(item.monto)}
              </span>
              <span className="text-[10px] text-slate-400 font-semibold w-9 text-right">
                {item.porcentaje}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
