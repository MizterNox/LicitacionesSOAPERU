// Panel de detalle (split-screen) — renderizado con el registro completo del mock.

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApp } from '../../store/AppState.jsx'
import { Icon } from '../ui/Icon.jsx'
import Timeline from './Timeline.jsx'
import { ScoreRing, TypeBadge, StatusBadge, RubroBadge } from './badges.jsx'
import { fmtPEN, fmtDate, daysUntil } from '../../utils/format.js'

function Meta({ label, value }) {
  return (
    <div className="bg-white p-3">
      <dt className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</dt>
      <dd className="mt-1 truncate text-[13px] font-semibold tabular-nums text-slate-900">{value}</dd>
    </div>
  )
}

function progressPct(bid) {
  const total = bid?.hitos?.length || 1
  return Math.min(100, Math.round(((bid?.fase_actual || 1) / total) * 100))
}

function OfferCallout({ bid }) {
  const offer = bid?.hitos?.[3] || bid?.hitos?.[1] || bid?.hitos?.[0]
  if (!offer) return null
  if (bid.fase_actual >= 4) {
    return (
      <div className="mt-4 flex items-center gap-2.5 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
        <Icon name="check" className="h-4 w-4 shrink-0 text-emerald-500" />
        <p className="leading-relaxed">
          <span className="font-bold text-slate-800">Ofertas presentadas</span> — el proceso ya está en fase de{' '}
          {bid.fase_actual >= 5 ? 'otorgamiento de la buena pro' : 'evaluación por el comité'}.
        </p>
      </div>
    )
  }
  const d = daysUntil(offer.fecha)
  const isPast = d < 0
  const box = isPast
    ? 'border-slate-200 bg-slate-50 text-slate-600'
    : d <= 1
    ? 'border-red-200 bg-red-50 text-red-700'
    : d <= 4
    ? 'border-amber-200 bg-amber-50 text-amber-800'
    : 'border-brand-200 bg-brand-50/70 text-brand-800'
  const ico = isPast ? 'text-slate-400' : d <= 1 ? 'text-red-500' : d <= 4 ? 'text-amber-500' : 'text-brand-500'
  const head = isPast
    ? 'Plazo concluido'
    : d === 0
    ? 'Hoy es el plazo límite'
    : d === 1
    ? 'Mañana cierra el plazo'
    : `Quedan ${d} días`
  return (
    <div className={`mt-4 flex items-center gap-3 rounded-xl border ${box} p-3`}>
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white/80 shadow-sm">
        <Icon name="clock" className={`h-4 w-4 ${ico}`} />
      </span>
      <div className="min-w-0 flex-1 text-xs leading-relaxed">
        <p className="font-bold">{head} para la presentación de ofertas</p>
        <p className="opacity-80">
          Fecha límite: <span className="font-bold tabular-nums">{fmtDate(offer.fecha)}</span> · {bid.modalidad}
        </p>
      </div>
      <button className="btn-secondary h-8 shrink-0 px-2.5 text-xs">
        <Icon name="download" className="h-3.5 w-3.5" /> Bases
      </button>
    </div>
  )
}

export default function DetailPanel({ bid }) {
  const { dispatch } = useApp()
  const [showOriginal, setShowOriginal] = useState(false)
  const close = () => dispatch({ type: 'CLOSE_DETAIL' })
  const matchTone = bid.match_score >= 85 ? 'text-emerald-600' : bid.match_score >= 60 ? 'text-brand-600' : 'text-slate-400'
  const matchLabel = bid.match_score >= 85 ? 'Alta' : bid.match_score >= 60 ? 'Media' : 'Baja'

  return (
    <aside
      id="detail-panel"
      role="complementary"
      aria-label="Detalle de la licitación"
      className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[440px] flex-col bg-white shadow-2xl sm:max-w-[460px] xl:static xl:z-auto xl:w-[420px] xl:max-w-none xl:shrink-0 xl:border-l xl:border-slate-200 xl:shadow-panel-l 2xl:w-[520px]"
    >
      {/* Header */}
      <div className="shrink-0 border-b border-slate-200 bg-gradient-to-br from-slate-50 to-white px-5 py-4">
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <TypeBadge tipo={bid.tipo_proceso} />
              <span className="font-mono text-[11px] font-semibold tracking-tight text-slate-400">{bid.codigo_seace}</span>
              <StatusBadge estado={bid.estado} />
              {bid.rubro && <RubroBadge rubro={bid.rubro} />}
            </div>
            <h2 className="mt-2 text-[15px] font-bold leading-snug text-slate-900">{bid.objeto}</h2>

            {/* Palabras clave extraídas por IA */}
            {bid.palabras_clave && bid.palabras_clave.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {bid.palabras_clave.map((kw) => (
                  <span key={kw} className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
                    #{kw}
                  </span>
                ))}
              </div>
            )}

            {/* Toggle para comparar con descripción original cruda */}
            {bid.descripcion_original && bid.descripcion_original !== bid.descripcion_limpia && (
              <div className="mt-2.5">
                <button
                  type="button"
                  onClick={() => setShowOriginal(!showOriginal)}
                  className="text-[11px] font-semibold text-brand-600 hover:text-brand-700 hover:underline flex items-center gap-1"
                >
                  <Icon name="file-text" className="h-3 w-3" />
                  {showOriginal ? 'Ocultar texto original OECE' : 'Ver texto original sin procesar'}
                </button>
                {showOriginal && (
                  <div className="mt-1.5 rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-600 font-mono leading-relaxed max-h-36 overflow-y-auto scroll-thin">
                    <p className="text-[10px] font-bold uppercase text-slate-400 mb-1">Texto crudo de la API gubernamental:</p>
                    {bid.descripcion_original}
                  </div>
                )}
              </div>
            )}

            <p className="mt-2 flex items-center gap-1.5 text-xs text-slate-500">
              <Icon name="building-2" className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{bid.entidad}</span>
              <span className="text-slate-300">·</span>
              <span className="shrink-0">{bid.region}</span>
            </p>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <Link
              to={`/licitaciones/${bid.ocid}`}
              className="icon-btn h-8 w-8 text-slate-500 hover:text-brand-600 hover:bg-brand-50 transition-colors"
              title="Abrir en página completa / enlace compartible"
            >
              <Icon name="external-link" className="h-4 w-4" />
            </Link>
            <button onClick={close} className="icon-btn h-8 w-8" title="Cerrar panel (Esc)">
              <Icon name="x" className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Match IA */}
        <div className="mt-3.5 flex items-center gap-3 rounded-xl border border-brand-100 bg-brand-50/60 p-3">
          <ScoreRing p={bid.match_score} className="h-11 w-11" />
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline justify-between gap-2">
              <p className="flex items-center gap-1.5 text-xs font-bold text-brand-900">
                <Icon name="sparkles" className="h-3.5 w-3.5 text-brand-500" /> Match IA · Relevancia
              </p>
              <p className={`text-[11px] font-semibold ${matchTone}`}>{matchLabel}</p>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-brand-100">
              <div className="h-full rounded-full bg-gradient-to-r from-brand-500 to-fuchsia-500" style={{ width: `${bid.match_score}%` }} />
            </div>
          </div>
        </div>
      </div>

      {/* Cuerpo scrolleable */}
      <div className="min-h-0 flex-1 overflow-y-auto scroll-thin">
        {/* Card Menor Cuantía */}
        {bid.es_menor_cuantia && (
          <div className="mx-5 mt-4 rounded-xl border border-emerald-200 bg-emerald-50/70 p-3 text-xs text-emerald-900">
            <div className="flex items-center gap-2 font-bold text-emerald-800">
              <Icon name="zap" className="h-4 w-4 text-emerald-600" />
              <span>Oportunidad de Menor Cuantía (≤ 8 UIT / S/ 42,800)</span>
            </div>
            <p className="mt-1 leading-relaxed text-emerald-700">
              Proceso ágil con plazos cortos de cotización. Ideal para adjudicación directa o simplificada sin requisitos de licitación pesada.
            </p>
          </div>
        )}

        <dl className="mx-5 mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-slate-200 bg-slate-200">
          <Meta label="Valor estimado" value={bid.valor_estimado != null ? fmtPEN(bid.valor_estimado) : 'No disponible'} />
          <Meta label="Tipo / Modalidad" value={`${bid.tipo_proceso || bid.modalidad} · ${bid.tipo_objeto || 'Servicios'}`} />
          <Meta label="CUI / Código SEACE" value={bid.cui || bid.codigo_seace || 'Sin CUI'} />
          <Meta label="Publicación" value={fmtDate(bid.fecha_publicacion)} />
        </dl>

        {/* Ítems y Requerimientos Normalizados OCDS */}
        {bid.items && bid.items.length > 0 && (
          <section className="px-5 pt-6">
            <div className="flex items-center justify-between">
              <h3 className="text-[13px] font-bold text-slate-900">
                Ítems de Contratación ({bid.items.length})
              </h3>
              <span className="text-[11px] font-medium text-slate-400">CUBSO / Cantidades</span>
            </div>
            <div className="mt-3 space-y-2">
              {bid.items.map((it, idx) => (
                <div key={it.id || idx} className="rounded-xl border border-slate-200 bg-white p-3 text-xs">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-semibold text-slate-800 leading-snug">{it.descripcion || `Ítem #${idx + 1}`}</span>
                    {it.codigo_cubso && (
                      <span className="shrink-0 font-mono text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded border border-slate-200" title="Código CUBSO">
                        CUBSO {it.codigo_cubso}
                      </span>
                    )}
                  </div>
                  <div className="mt-2 flex items-center gap-3 text-[11px] text-slate-500">
                    {it.cantidad != null && (
                      <span><strong>Cantidad:</strong> {it.cantidad} {it.unidad || 'UND'}</span>
                    )}
                    {it.estado && (
                      <span><strong>Estado:</strong> {it.estado}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Línea de tiempo */}
        <section className="px-5 pt-6">
          <div className="flex items-center justify-between">
            <h3 className="text-[13px] font-bold text-slate-900">Línea de tiempo · SEACE</h3>
            <span className="chip bg-slate-100 text-slate-500">
              Fase {Math.min((bid.fase_actual || 0) + 1, bid.hitos?.length || 1)} / {bid.hitos?.length || 1}
            </span>
          </div>

          <div className="mt-3">
            <div className="flex items-center justify-between text-[11px] font-semibold">
              <span className="text-slate-500">Progreso del proceso</span>
              <span className="tabular-nums text-slate-700">{progressPct(bid)}%</span>
            </div>
            <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 via-brand-500 to-brand-600" style={{ width: `${progressPct(bid)}%` }} />
            </div>
          </div>

          <OfferCallout bid={bid} />

          <div className="mt-4">
            <Timeline bid={bid} />
          </div>
        </section>

        {/* Documentos */}
        <section className="px-5 pt-6">
          <div className="flex items-center justify-between">
            <h3 className="text-[13px] font-bold text-slate-900">Documentos oficiales</h3>
            <span className="text-[11px] text-slate-400 font-medium">{bid.documentos?.length || 0} disponibles</span>
          </div>
          <ul className="mt-3 space-y-2">
            {(bid.documentos || []).map((d, dIdx) => (
              <li key={d.id || d.nombre || dIdx} className="group flex items-center gap-3 rounded-xl border border-slate-200 p-2.5 transition-colors hover:border-brand-300 hover:bg-brand-50/40">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-rose-50 text-rose-500">
                  <Icon name="file-text" className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13px] font-semibold text-slate-800">{d.nombre}</p>
                  <p className="text-[11px] text-slate-400">
                    {d.formato || 'PDF'} {d.actualizado ? `· Act. ${d.actualizado}` : ''}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1">
                  {d.url ? (
                    <a
                      href={d.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-secondary h-8 px-2 text-xs flex items-center gap-1"
                      title="Abrir documento oficial"
                    >
                      <Icon name="download" className="h-3.5 w-3.5" /> Ver
                    </a>
                  ) : (
                    <span className="text-[10px] text-slate-400 italic">En SEACE</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>

        {/* ¿Por qué te sugerimos? (IA) */}
        <section className="px-5 pb-5 pt-6">
          <div className="relative overflow-hidden rounded-xl bg-ink-950 p-4">
            <div className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full bg-brand-500/25 blur-2xl"></div>
            <h3 className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-brand-300">
              <Icon name="sparkles" className="h-3.5 w-3.5" /> Análisis IA de Oportunidad
            </h3>
            <ul className="mt-3 space-y-2">
              {(bid.motivos_ia || []).map((r, mIdx) => (
                <li key={mIdx} className="flex gap-2 text-xs leading-relaxed text-ink-200">
                  <span className="mt-0.5 shrink-0 text-emerald-400">
                    <Icon name="check" className="h-3.5 w-3.5" />
                  </span>
                  {r}
                </li>
              ))}
            </ul>
            <div className="mt-3.5 flex items-center justify-between border-t border-white/10 pt-3">
              <span className="text-[11px] font-medium text-ink-400">Confianza del modelo</span>
              <span className="text-[11px] font-bold text-white">{bid.match_score}%</span>
            </div>
          </div>
        </section>
      </div>

      {/* Footer sticky */}
      <div className="flex shrink-0 gap-2.5 border-t border-slate-200 bg-white px-5 py-3.5">
        <a
          href={
            bid.documentos?.find((d) => d.url)?.url ||
            'https://prodapp2.seace.gob.pe/seacebus-uiwd-pub/buscadorConvocatorias/buscadorConvocatorias.xhtml'
          }
          target="_blank"
          rel="noopener noreferrer"
          className="btn-primary flex-1 justify-center"
        >
          <Icon name="download" className="h-4 w-4" /> Bases Oficiales
        </a>
        <a
          href="https://prodapp2.seace.gob.pe/seacebus-uiwd-pub/buscadorConvocatorias/buscadorConvocatorias.xhtml"
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary flex-1 justify-center"
        >
          <Icon name="gavel" className="h-4 w-4" /> Ver en SEACE
        </a>
      </div>
    </aside>
  )
}
