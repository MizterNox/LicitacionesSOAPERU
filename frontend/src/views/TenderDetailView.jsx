// Vista de Detalle Completa y Compartible de Licitación (/licitaciones/:ocid)
// Diseño B2B corporativo de alta confiabilidad con 5 pestañas de inspección técnica.

import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useApp } from '../store/AppState.jsx'
import { tendersApi } from '../lib/api.js'
import { Icon } from '../components/ui/Icon.jsx'
import { DetailSkeleton } from '../components/ui/Skeleton.jsx'
import { ScoreRing, TypeBadge, StatusBadge, RubroBadge, SoaPeruTagBadge, scoreTier } from '../components/dashboard/badges.jsx'
import Timeline from '../components/dashboard/Timeline.jsx'
import { fmtPEN, fmtDate, daysUntil } from '../utils/format.js'

export default function TenderDetailView() {
  const { ocid } = useParams()
  const navigate = useNavigate()
  const { state } = useApp()

  const [bid, setBid] = useState(() => {
    return state.convocatorias?.find((c) => c.ocid === ocid || c.id === ocid) || null
  })
  const [loading, setLoading] = useState(!bid)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('resumen')
  const [copied, setCopied] = useState(false)
  const [showOriginal, setShowOriginal] = useState(false)

  // Cargar detalle completo desde la API para asegurar frescura de datos
  useEffect(() => {
    let isMounted = true
    const fetchDetail = async () => {
      try {
        const data = await tendersApi.getLicitacionDetail(ocid)
        if (isMounted) {
          setBid(data)
          setLoading(false)
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || 'No se pudo cargar la licitación solicitada.')
          setLoading(false)
        }
      }
    }

    fetchDetail()
    return () => {
      isMounted = false
    }
  }, [ocid])

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-[1280px] p-4 md:p-6">
        <DetailSkeleton />
      </div>
    )
  }

  if (error || !bid) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center my-12 card space-y-4">
        <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-red-50 text-red-600">
          <Icon name="alert-triangle" className="h-6 w-6" />
        </span>
        <h2 className="text-lg font-bold text-slate-900">Licitación no encontrada</h2>
        <p className="text-sm text-slate-500">{error || `El proceso con OCID ${ocid} no existe en el sistema.`}</p>
        <button onClick={() => navigate('/dashboard')} className="btn-primary mx-auto">
          <Icon name="arrow-left" className="h-4 w-4" /> Volver al Dashboard
        </button>
      </div>
    )
  }

  const effectiveScore = bid.relevance_score ?? bid.match_score ?? 0
  const tier = scoreTier(effectiveScore, bid.primary_tag)
  const matchTone = tier.text
  const matchLabel = tier.label
  const dLimite = bid.fecha_limite ? daysUntil(bid.fecha_limite) : null

  return (
    <div className="mx-auto max-w-[1400px] space-y-5 p-4 md:p-6">
      {/* Breadcrumb de navegación */}
      <nav className="flex items-center gap-2 text-xs font-medium text-slate-500" aria-label="Breadcrumb">
        <Link to="/dashboard" className="hover:text-brand-600 transition-colors">
          Dashboard
        </Link>
        <Icon name="chevron-right" className="h-3.5 w-3.5 text-slate-400" />
        <Link to="/buscador" className="hover:text-brand-600 transition-colors">
          Convocatorias
        </Link>
        <Icon name="chevron-right" className="h-3.5 w-3.5 text-slate-400" />
        <span className="text-slate-800 font-semibold font-mono truncate max-w-[200px] sm:max-w-none">
          {bid.codigo_seace || bid.ocid}
        </span>
      </nav>

      {/* Cabecera Principal (Hero Card) */}
      <section className="card overflow-hidden bg-white shadow-sm border border-slate-200">
        <div className="p-5 md:p-6 space-y-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-2.5 min-w-0 flex-1">
              {/* Badges de clasificación */}
              <div className="flex flex-wrap items-center gap-2">
                <TypeBadge tipo={bid.tipo_proceso} />
                <span className="font-mono text-xs font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  {bid.codigo_seace}
                </span>
                <StatusBadge estado={bid.estado} />
                {bid.primary_tag && <SoaPeruTagBadge tag={bid.primary_tag} />}
                {(bid.is_minor_contract || bid.es_menor_cuantia) && (
                  <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-800 border border-emerald-300">
                    <Icon name="zap" className="h-3 w-3 text-emerald-600" /> ≤ 8 UIT (Menor Cuantía)
                  </span>
                )}
                {bid.rubro && <RubroBadge rubro={bid.rubro} />}
              </div>

              {/* Título de la licitación */}
              <h1 className="text-lg font-bold text-slate-900 leading-snug sm:text-xl lg:text-2xl">
                {bid.objeto}
              </h1>

              {/* Entidad convocante y ubicación */}
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600 pt-1">
                <span className="flex items-center gap-1.5 font-semibold text-slate-800">
                  <Icon name="building-2" className="h-4 w-4 text-brand-600" />
                  {bid.entidad}
                </span>
                {bid.entidad_ruc && (
                  <span className="font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
                    RUC: {bid.entidad_ruc}
                  </span>
                )}
                <span className="text-slate-300">·</span>
                <span className="flex items-center gap-1 text-slate-500">
                  <Icon name="map-pin" className="h-3.5 w-3.5" />
                  {bid.region || 'Nacional'}
                </span>
                <span className="text-slate-300">·</span>
                <span>Publicado el {fmtDate(bid.fecha_publicacion)}</span>
              </div>
            </div>

            {/* Match IA y Acciones rápidas */}
            <div className="flex flex-wrap items-center gap-3 shrink-0 lg:flex-col lg:items-end">
              <div className="flex items-center gap-3 rounded-xl border border-brand-100 bg-brand-50/70 p-3 shadow-xs">
                <ScoreRing p={effectiveScore} primaryTag={bid.primary_tag} className="h-10 w-10" />
                <div className="leading-tight">
                  <div className="flex items-center gap-1 text-xs font-bold text-brand-900">
                    <Icon name="sparkles" className="h-3.5 w-3.5 text-brand-500" /> Score SOAPERU
                  </div>
                  <span className={`text-[11px] font-semibold ${matchTone}`}>{matchLabel}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleCopyLink}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-xs"
                  title="Copiar enlace compartible al portapapeles"
                >
                  <Icon name={copied ? 'check' : 'copy'} className={`h-3.5 w-3.5 ${copied ? 'text-emerald-600' : 'text-slate-500'}`} />
                  <span>{copied ? '¡Enlace copiado!' : 'Compartir'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Grid de Metadatos Principales */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 border-t border-slate-100 pt-4 text-xs">
            <div className="rounded-xl border border-slate-200/80 bg-slate-50 p-3">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Valor Estimado</span>
              <span className="mt-1 text-sm font-extrabold text-slate-900 tabular-nums block">
                {bid.valor_estimado != null ? fmtPEN(bid.valor_estimado) : 'N/D'}
              </span>
            </div>
            <div className="rounded-xl border border-slate-200/80 bg-slate-50 p-3">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Plazo de Ofertas</span>
              <span className={`mt-1 text-sm font-extrabold tabular-nums block ${dLimite != null && dLimite <= 2 ? 'text-red-600' : 'text-slate-900'}`}>
                {bid.fecha_limite ? fmtDate(bid.fecha_limite) : 'No especificado'}
                {dLimite != null && dLimite >= 0 && (
                  <span className="ml-1 text-[11px] font-semibold text-slate-500">
                    ({dLimite === 0 ? 'Cierra hoy' : dLimite === 1 ? '1 día restante' : `${dLimite} días restantes`})
                  </span>
                )}
              </span>
            </div>
            <div className="rounded-xl border border-slate-200/80 bg-slate-50 p-3">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Objeto de Contratación</span>
              <span className="mt-1 text-sm font-bold text-slate-800 block">
                {bid.tipo_objeto || 'Servicios'}
              </span>
            </div>
            <div className="rounded-xl border border-slate-200/80 bg-slate-50 p-3">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">CUI / Identificador</span>
              <span className="mt-1 text-sm font-bold text-slate-800 font-mono block">
                {bid.cui || 'No aplica'}
              </span>
            </div>
          </div>
        </div>

        {/* Pestañas de Navegación del Detalle */}
        <div className="flex border-t border-slate-200 bg-slate-50 px-4 md:px-6 overflow-x-auto scroll-thin">
          {[
            { id: 'resumen', label: 'Resumen & Análisis IA', icon: 'sparkles' },
            { id: 'items', label: `Requerimientos e Ítems (${bid.items?.length || 0})`, icon: 'box' },
            { id: 'cronograma', label: 'Cronograma & Plazos', icon: 'clock' },
            { id: 'documentos', label: `Documentos Oficiales (${bid.documentos?.length || 0})`, icon: 'file-text' },
            { id: 'tecnico', label: 'Ficha Técnica OCDS', icon: 'code' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 border-b-2 px-3 py-3 text-xs font-bold transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-brand-600 text-brand-700 bg-white'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <Icon name={tab.icon} className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </section>

      {/* Contenido de las Pestañas */}
      <section className="space-y-4">
        {/* Pestaña 1: Resumen & Análisis IA */}
        {activeTab === 'resumen' && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="card p-5 space-y-4 lg:col-span-2">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Icon name="file-text" className="h-4 w-4 text-brand-600" />
                Descripción del Requerimiento
              </h2>
              <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4 text-sm text-slate-700 leading-relaxed">
                {bid.descripcion_limpia || bid.objeto}
              </div>

              {/* Comparador con texto original crudo */}
              {bid.descripcion_original && bid.descripcion_original !== bid.descripcion_limpia && (
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={() => setShowOriginal(!showOriginal)}
                    className="text-xs font-semibold text-brand-600 hover:underline flex items-center gap-1.5"
                  >
                    <Icon name="eye" className="h-3.5 w-3.5" />
                    {showOriginal ? 'Ocultar texto crudo de la fuente' : 'Auditar texto original sin procesar (OECE / SEACE)'}
                  </button>
                  {showOriginal && (
                    <div className="mt-2 rounded-xl border border-slate-200 bg-slate-100/80 p-3 font-mono text-xs text-slate-600 leading-relaxed max-h-48 overflow-y-auto">
                      <p className="font-bold text-[10px] uppercase text-slate-400 mb-1">Payload original crudo:</p>
                      {bid.descripcion_original}
                    </div>
                  )}
                </div>
              )}

              {/* Palabras clave extraídas */}
              {bid.palabras_clave && bid.palabras_clave.length > 0 && (
                <div className="pt-2">
                  <span className="text-xs font-bold text-slate-500 block mb-2">Términos Clave Extraídos por IA:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {bid.palabras_clave.map((kw) => (
                      <span key={kw} className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700 border border-slate-200">
                        #{kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Tarjeta de Justificación IA */}
            <div className="card p-5 space-y-4 bg-gradient-to-br from-ink-950 to-slate-900 text-white relative overflow-hidden">
              <div className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-brand-500/20 blur-2xl" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-brand-300 flex items-center gap-2">
                <Icon name="sparkles" className="h-4 w-4" />
                Análisis de Oportunidad IA
              </h2>
              <ul className="space-y-2.5 text-xs text-slate-200 leading-relaxed">
                {(bid.motivos_ia || []).map((m, idx) => (
                  <li key={idx} className="flex gap-2">
                    <span className="mt-0.5 shrink-0 text-emerald-400">
                      <Icon name="check" className="h-4 w-4" />
                    </span>
                    <span>{m}</span>
                  </li>
                ))}
              </ul>

              <div className="border-t border-white/10 pt-3 flex items-center justify-between text-xs">
                <span className="text-slate-400">Confianza de clasificación:</span>
                <span className="font-bold text-white tabular-nums">
                  {bid.rubro_confianza ? `${Math.round(bid.rubro_confianza * 100)}%` : '85%'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Pestaña 2: Requerimientos e Ítems OCDS */}
        {activeTab === 'items' && (
          <div className="card p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-sm font-bold text-slate-900">
                  Desglose de Ítems del Proceso (CUBSO)
                </h2>
                <p className="text-xs text-slate-500">
                  Catálogo Único de Bienes, Servicios y Obras registrado en las bases del Estado.
                </p>
              </div>
            </div>

            {bid.items && bid.items.length > 0 ? (
              <div className="overflow-x-auto scroll-thin">
                <table className="w-full min-w-[650px] text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 font-bold text-slate-500 uppercase text-[10px]">
                      <th className="px-3 py-2">Ítem</th>
                      <th className="px-3 py-2">Código CUBSO</th>
                      <th className="px-3 py-2">Descripción del Requerimiento</th>
                      <th className="px-3 py-2 text-right">Cantidad</th>
                      <th className="px-3 py-2">Unidad</th>
                      <th className="px-3 py-2">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {bid.items.map((it, idx) => (
                      <tr key={it.id || idx} className="hover:bg-slate-50/60">
                        <td className="px-3 py-2.5 font-bold text-slate-700">#{idx + 1}</td>
                        <td className="px-3 py-2.5 font-mono text-slate-800 font-semibold">
                          {it.codigo_cubso || 'N/E'}
                        </td>
                        <td className="px-3 py-2.5 font-medium text-slate-800 leading-snug">
                          {it.descripcion || 'Sin descripción detallada'}
                        </td>
                        <td className="px-3 py-2.5 text-right font-bold text-slate-900 tabular-nums">
                          {it.cantidad != null ? it.cantidad : '—'}
                        </td>
                        <td className="px-3 py-2.5 text-slate-600">
                          {it.unidad || 'UND'}
                        </td>
                        <td className="px-3 py-2.5">
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                            {it.estado || 'Activo'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-8 text-center text-slate-500 text-xs">
                No se registraron ítems individuales en el release OCDS; consulta las bases completas del proceso.
              </div>
            )}
          </div>
        )}

        {/* Pestaña 3: Cronograma & Plazos */}
        {activeTab === 'cronograma' && (
          <div className="card p-5 space-y-5">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Cronograma del Procedimiento</h2>
              <p className="text-xs text-slate-500">
                Fases de convocatoria, consultas y presentación electrónica de ofertas.
              </p>
            </div>
            <Timeline bid={bid} />
          </div>
        )}

        {/* Pestaña 4: Documentos Oficiales */}
        {activeTab === 'documentos' && (
          <div className="card p-5 space-y-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Documentos y Bases del Proceso</h2>
              <p className="text-xs text-slate-500">
                Archivos oficiales publicados en la plataforma de contrataciones abiertas del Estado.
              </p>
            </div>

            {bid.documentos && bid.documentos.length > 0 ? (
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                {bid.documentos.map((doc, idx) => (
                  <div key={doc.id || idx} className="flex items-center justify-between rounded-xl border border-slate-200 p-3 bg-white hover:border-brand-300 transition-colors">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-rose-50 text-rose-600">
                        <Icon name="file-text" className="h-4 w-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-bold text-slate-800 leading-snug">{doc.nombre}</p>
                        <p className="text-[11px] text-slate-400">
                          {doc.formato || 'PDF'} {doc.actualizado ? `· ${doc.actualizado}` : ''}
                        </p>
                      </div>
                    </div>
                    {doc.url ? (
                      <a
                        href={doc.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-secondary h-8 px-2.5 text-xs shrink-0 flex items-center gap-1 shadow-xs"
                      >
                        <Icon name="download" className="h-3.5 w-3.5" /> Descargar
                      </a>
                    ) : (
                      <span className="text-[11px] text-slate-400 italic shrink-0">En portal SEACE</span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-8 text-center text-slate-500 text-xs">
                No hay documentos directos en el release; accede al portal SEACE para descargar las bases.
              </div>
            )}
          </div>
        )}

        {/* Pestaña 5: Ficha Técnica OCDS */}
        {activeTab === 'tecnico' && (
          <div className="card p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-900 font-mono">Payload JSON OCDS (Open Contracting Data Standard)</h2>
                <p className="text-xs text-slate-500">Estructura oficial extraída desde la API del OECE.</p>
              </div>
              <button
                type="button"
                onClick={() => navigator.clipboard.writeText(JSON.stringify(bid.raw_payload || bid, null, 2))}
                className="btn-secondary h-8 text-xs flex items-center gap-1"
              >
                <Icon name="copy" className="h-3.5 w-3.5" /> Copiar JSON
              </button>
            </div>
            <pre className="max-h-96 overflow-y-auto rounded-xl border border-slate-200 bg-slate-900 p-4 font-mono text-[11px] text-emerald-400 scroll-thin leading-relaxed">
              {JSON.stringify(bid.raw_payload || bid, null, 2)}
            </pre>
          </div>
        )}
      </section>

      {/* Barra de Acciones Fijas Inferiores */}
      <footer className="sticky bottom-4 z-20 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-xl backdrop-blur-md">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="btn-ghost h-9 px-3 text-xs flex items-center gap-1"
          >
            <Icon name="arrow-left" className="h-4 w-4" /> Regresar
          </button>
        </div>

        <div className="flex items-center gap-2.5">
          <a
            href={
              bid.documentos?.find((d) => d.url)?.url ||
              'https://prodapp2.seace.gob.pe/seacebus-uiwd-pub/buscadorConvocatorias/buscadorConvocatorias.xhtml'
            }
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary h-9 px-4 text-xs flex items-center gap-1.5 shadow-sm"
          >
            <Icon name="download" className="h-4 w-4" /> Descargar Bases Oficiales
          </a>
          <a
            href="https://prodapp2.seace.gob.pe/seacebus-uiwd-pub/buscadorConvocatorias/buscadorConvocatorias.xhtml"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary h-9 px-4 text-xs flex items-center gap-1.5 shadow-sm"
          >
            <Icon name="gavel" className="h-4 w-4" /> Postular en SEACE
          </a>
        </div>
      </footer>
    </div>
  )
}
