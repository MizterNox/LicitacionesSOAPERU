import { useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { fmtPEN } from '../../utils/format.js'
import { Icon } from '../ui/Icon.jsx'

const TIPO_COLORS = {
  Servicios: '#8B5CF6',
  Bienes: '#06B6D4',
  Obras: '#F59E0B',
}

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

const PALETTE = ['#8B5CF6', '#06B6D4', '#10B981', '#F59E0B', '#EC4899', '#6366F1', '#3B82F6', '#14B8A6']

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null

  const totalCount = payload.reduce((acc, p) => acc + (Number(p.value) || 0), 0)
  const totalMonto = payload.reduce((acc, p) => {
    const m = p.payload?.[`monto_${p.dataKey}`] || 0
    return acc + Number(m)
  }, 0)

  return (
    <div className="rounded-xl border border-slate-200/80 bg-white/95 p-3 shadow-xl backdrop-blur-md">
      <div className="border-b border-slate-100 pb-1.5 mb-2">
        <p className="text-xs font-bold text-slate-800">{label}</p>
        <p className="text-[11px] text-slate-400">
          {totalCount} procesos · {fmtPEN(totalMonto)}
        </p>
      </div>
      <div className="space-y-1.5">
        {payload.map((entry, index) => {
          const count = entry.value
          if (!count) return null
          const monto = entry.payload?.[`monto_${entry.dataKey}`] || 0
          return (
            <div key={`tip-${index}`} className="flex items-center justify-between gap-4 text-xs">
              <span className="flex items-center gap-1.5">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="font-medium text-slate-700">{entry.name}</span>
              </span>
              <span className="text-right tabular-nums">
                <span className="font-bold text-slate-900">{count}</span>
                <span className="text-[11px] text-slate-400 ml-1.5">({fmtPEN(monto)})</span>
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function MonthlyVolumeChart({ data, grupos, groupBy, onGroupByChange, meses, onMesesChange }) {
  const isTipo = groupBy === 'tipo'

  const getColor = (grupo, index) => {
    if (isTipo && TIPO_COLORS[grupo]) return TIPO_COLORS[grupo]
    if (!isTipo && RUBRO_COLORS[grupo]) return RUBRO_COLORS[grupo]
    return PALETTE[index % PALETTE.length]
  }

  return (
    <div className="card p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand-50 text-brand-600">
              <Icon name="chart" className="h-4 w-4" />
            </span>
            <h3 className="text-sm font-bold text-slate-900">Volumen Mensual de Convocatorias</h3>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Distribución temporal de licitaciones públicas según {isTipo ? 'objeto contractual' : 'rubro clasificado por IA'}.
          </p>
        </div>

        {/* Controles de agrupación y periodo */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Switch Tipo / Rubro */}
          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100/80 p-0.5 text-xs">
            <button
              onClick={() => onGroupByChange('tipo')}
              className={`rounded-md px-2.5 py-1 font-semibold transition-all ${
                isTipo ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              Por Objeto
            </button>
            <button
              onClick={() => onGroupByChange('rubro')}
              className={`rounded-md px-2.5 py-1 font-semibold transition-all ${
                !isTipo ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              Por Rubro IA
            </button>
          </div>

          {/* Selector de meses */}
          <select
            value={meses}
            onChange={(e) => onMesesChange(Number(e.target.value))}
            className="field h-7 appearance-none rounded-lg text-xs pr-6"
          >
            <option value={6}>Últimos 6 meses</option>
            <option value={12}>Últimos 12 meses</option>
            <option value={24}>Últimos 24 meses</option>
          </select>
        </div>
      </div>

      {/* Gráfico */}
      <div className="h-[300px] w-full overflow-x-auto scroll-thin">
        <div className="h-full min-w-[280px]">
          {data && data.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
              data={data}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            >
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
                allowDecimals={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(139, 92, 246, 0.05)' }} />
              <Legend
                wrapperStyle={{ paddingTop: 12, fontSize: 11 }}
                iconType="circle"
                iconSize={8}
              />
              {(grupos || []).map((grupo, idx) => (
                <Bar
                  key={grupo}
                  dataKey={grupo}
                  name={grupo}
                  stackId="a"
                  fill={getColor(grupo, idx)}
                  radius={idx === (grupos.length - 1) ? [4, 4, 0, 0] : [0, 0, 0, 0]}
                  maxBarSize={48}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="grid h-full place-items-center text-xs text-slate-400">
            No hay convocatorias registradas en este periodo.
          </div>
        )}
        </div>
      </div>
    </div>
  )
}
