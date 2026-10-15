// Línea de tiempo vertical DETALLADA de hitos SEACE (columna JSONB `hitos`).
// Estados: completado → en curso (pulso + tarjeta) → pendiente.

import { Icon } from '../ui/Icon.jsx'
import { TODAY, parseISO, fmtDate, fmtDateShort } from '../../utils/format.js'

const MILESTONE_META = [
  { icon: 'megaphone', desc: 'El órgano emite la convocatoria en el portal SEACE' },
  { icon: 'message-square', desc: 'Los postores pueden formular consultas a las bases' },
  { icon: 'file-text', desc: 'El comité técnico publica la absolución de consultas' },
  { icon: 'pen-line', desc: 'Fecha límite para entregar la oferta técnica y económica' },
  { icon: 'scale', desc: 'Apertura de sobres y evaluación por el comité técnico' },
  { icon: 'gavel', desc: 'Se notifica la adjudicación al postor ganador' },
]

function Chip({ m, idx, phase }) {
  if (idx < phase) return <span className="chip bg-emerald-50 text-emerald-600">Completado</span>
  if (idx === phase) {
    const start = parseISO(m.fecha)
    const end = m.fin ? parseISO(m.fin) : start
    if (TODAY >= start && TODAY <= end)
      return <span className="chip bg-brand-600 text-white shadow-sm shadow-brand-600/30">En curso · hoy</span>
    const d = Math.round((start - TODAY) / 86400000)
    return <span className="chip bg-brand-600 text-white shadow-sm shadow-brand-600/30">En {d} día{d === 1 ? '' : 's'}</span>
  }
  const d = Math.round((parseISO(m.fecha) - TODAY) / 86400000)
  if (d <= 0) return <span className="chip bg-slate-100 text-slate-400">Pendiente</span>
  if (d <= 4)
    return <span className="chip bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/15">En {d} día{d === 1 ? '' : 's'}</span>
  return <span className="chip bg-slate-100 text-slate-500">En {d} día{d === 1 ? '' : 's'}</span>
}

function Node({ m, idx, phase }) {
  const meta = MILESTONE_META[idx] ?? MILESTONE_META[0]
  const ico = <Icon name={meta.icon} className="h-3.5 w-3.5" />
  if (idx < phase)
    return <span className="grid h-[26px] w-[26px] shrink-0 place-items-center rounded-full bg-emerald-500 text-white ring-4 ring-emerald-500/10">{ico}</span>
  if (idx === phase)
    return <span className="timeline-pulse relative z-10 grid h-[26px] w-[26px] shrink-0 place-items-center rounded-full border-2 border-brand-500 bg-white text-brand-600">{ico}</span>
  return <span className="grid h-[26px] w-[26px] shrink-0 place-items-center rounded-full border-2 border-slate-200 bg-white text-slate-300">{ico}</span>
}

export default function Timeline({ bid }) {
  const hitos = bid?.hitos || []
  return (
    <ol className="relative">
      {hitos.map((m, i) => {
        const done = i < (bid?.fase_actual || 0)
        const current = i === (bid?.fase_actual || 0)
        const last = i === hitos.length - 1
        const meta = MILESTONE_META[i] ?? MILESTONE_META[0]
        const label = m.fin ? `${fmtDateShort(m.fecha)} – ${fmtDateShort(m.fin)}` : fmtDate(m.fecha)
        return (
          <li key={`${m.nombre}-${i}`} className="relative flex gap-3.5 pb-5 last:pb-0">
            {!last && (
              <span className={`absolute left-[12px] top-[30px] h-[calc(100%-30px)] w-0.5 ${done ? 'bg-emerald-200' : 'bg-slate-200'}`}></span>
            )}
            <Node m={m} idx={i} phase={bid.fase_actual} />
            <div
              className={`-mt-px min-w-0 flex-1 ${
                current ? '-mx-2.5 -mt-1 rounded-xl bg-gradient-to-r from-brand-50/90 via-brand-50/40 to-transparent px-2.5 py-2 ring-1 ring-brand-100' : ''
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
                <p className={`text-[13px] font-bold ${done ? 'text-slate-400' : current ? 'text-slate-900' : 'text-slate-600'}`}>{m.nombre}</p>
                <Chip m={m} idx={i} phase={bid.fase_actual} />
              </div>
              <p className={`mt-0.5 text-xs leading-snug ${done ? 'text-slate-400' : 'text-slate-500'}`}>{meta.desc}</p>
              <p className="mt-1 flex items-center gap-1 text-[11px] font-medium text-slate-400">
                <Icon name="calendar" className="h-3 w-3" />
                {label}
              </p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
