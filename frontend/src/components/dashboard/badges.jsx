// Átomos visuales: TypeBadge, StatusBadge, ScoreRing, ScoreCell, TipoObjetoBadge.

import { Icon } from '../ui/Icon.jsx'

// Tipo de proceso SEACE
const TYPE_STYLES = {
  LP: 'bg-brand-50 text-brand-700 ring-brand-600/15',
  CP: 'bg-sky-50 text-sky-700 ring-sky-600/15',
  AS: 'bg-amber-50 text-amber-700 ring-amber-600/15',
  MS: 'bg-emerald-50 text-emerald-700 ring-emerald-600/15',
  MC: 'bg-slate-100 text-slate-600 ring-slate-500/15',
}

export function TypeBadge({ tipo }) {
  return <span className={`chip ring-1 ring-inset ${TYPE_STYLES[tipo] ?? TYPE_STYLES.MC}`}>{tipo}</span>
}

// Estado del proceso (enum PostgreSQL: Vigente / Finalizado)
export function StatusBadge({ estado }) {
  const vig = estado === 'Vigente'
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold ${
        vig ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${vig ? 'bg-emerald-500' : 'bg-slate-400'}`}></span>
      {estado}
    </span>
  )
}

// ---- Match Score de IA ----
export function scoreTier(p) {
  if (p >= 85) return { label: 'Alta', color: '#10b981', glow: 'rgba(16,185,129,.28)', text: 'text-emerald-600' }
  if (p >= 60) return { label: 'Media', color: '#8b5cf6', glow: 'rgba(139,92,246,.30)', text: 'text-brand-600' }
  return { label: 'Baja', color: '#94a3b8', glow: 'rgba(100,116,139,.20)', text: 'text-slate-500' }
}

export function ScoreRing({ p, className = 'h-10 w-10' }) {
  const t = scoreTier(p)
  return (
    <span
      className={`score-ring ${className}`}
      style={{ '--score': p, '--score-color': t.color, '--score-glow': t.glow }}
      title={`Match IA: ${p}%`}
      role="img"
      aria-label={`Relevancia ${p} por ciento, ${t.label.toLowerCase()}`}
    >
      <span className={`score-ring__inner text-[11px] font-extrabold tabular-nums ${t.text}`}>{p}%</span>
    </span>
  )
}

// Celda de la tabla: anillo resaltado + tier (Alta / Media / Baja)
export function ScoreCell({ p }) {
  const t = scoreTier(p)
  return (
    <div className="flex flex-col items-center gap-1" title={`Match IA: ${p}% — Relevancia ${t.label.toLowerCase()}`}>
      <ScoreRing p={p} className="h-10 w-10 transition-transform duration-200 group-hover:scale-110" />
      <span className={`text-[9px] font-extrabold uppercase tracking-[0.1em] ${t.text}`}>{t.label}</span>
    </div>
  )
}

// Tipo de objeto (enum PostgreSQL: Bienes / Servicios / Obras)
const TIPO_OBJETO_ICON = { Bienes: 'box', Servicios: 'briefcase', Obras: 'hammer' }

export function TipoObjetoBadge({ tipo }) {
  return (
    <span className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-slate-400">
      <Icon name={TIPO_OBJETO_ICON[tipo] ?? 'box'} className="h-3 w-3" />
      {tipo}
    </span>
  )
}
