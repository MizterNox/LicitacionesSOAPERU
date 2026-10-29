import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { fmtPEN } from '../../utils/format.js'
import { Icon } from '../ui/Icon.jsx'

function AmountTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null
  const data = payload[0].payload

  return (
    <div className="rounded-xl border border-slate-200/80 bg-white/95 p-3 shadow-xl backdrop-blur-md text-xs">
      <p className="font-bold text-slate-800">{label}</p>
      <div className="mt-1.5 space-y-1">
        <p className="flex justify-between gap-4 text-slate-600">
          <span>Presupuesto total:</span>
          <span className="font-extrabold text-brand-700 tabular-nums">{fmtPEN(data.monto)}</span>
        </p>
        <p className="flex justify-between gap-4 text-slate-500 text-[11px]">
          <span>Convocatorias:</span>
          <span className="font-semibold text-slate-800 tabular-nums">{data.total}</span>
        </p>
      </div>
    </div>
  )
}

function formatMontoAxis(value) {
  if (value >= 1_000_000) return `S/ ${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `S/ ${(value / 1_000).toFixed(0)}k`
  return `S/ ${value}`
}

export function AmountTrendChart({ data }) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-emerald-50 text-emerald-600">
            <Icon name="banknote" className="h-4 w-4" />
          </span>
          <div>
            <h3 className="text-sm font-bold text-slate-900">Tendencia de Presupuesto Licitado</h3>
            <p className="text-xs text-slate-500">Monto total convocado por el Estado en Soles (PEN)</p>
          </div>
        </div>
      </div>

      <div className="h-[260px] w-full">
        {data && data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
              <defs>
                <linearGradient id="amountGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
              <XAxis
                dataKey="mes_label"
                stroke="#94A3B8"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#E2E8F0' }}
              />
              <YAxis
                stroke="#94A3B8"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={formatMontoAxis}
              />
              <Tooltip content={<AmountTooltip />} />
              <Area
                type="monotone"
                dataKey="monto"
                name="Monto Convocado"
                stroke="#10B981"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#amountGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="grid h-full place-items-center text-xs text-slate-400">
            Sin datos suficientes para graficar tendencia de presupuesto.
          </div>
        )}
      </div>
    </div>
  )
}
