import { useState, useEffect } from 'react'
import { alertsApi } from '../../lib/api.js'
import { useAuth } from '../../store/AuthContext.jsx'
import { useApp } from '../../store/AppState.jsx'
import { fmtPEN } from '../../utils/format.js'
import { Icon } from '../ui/Icon.jsx'
import { RubroBadge, TipoObjetoBadge } from '../dashboard/badges.jsx'

export function AlertsView() {
  const { user, isAuthenticated, openAuthModal } = useAuth()
  const { dispatch } = useApp()
  const [filters, setFilters] = useState([])
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('filtros') // 'filtros' | 'historial'

  const [testEmailStatus, setTestEmailStatus] = useState('idle')

  const handleSendTestEmail = async () => {
    setTestEmailStatus('sending')
    try {
      await alertsApi.sendTestAlert()
      setTestEmailStatus('success')
      setTimeout(() => setTestEmailStatus('idle'), 4000)
    } catch (err) {
      console.error('Error enviando correo de prueba:', err)
      setTestEmailStatus('error')
      setTimeout(() => setTestEmailStatus('idle'), 4000)
    }
  }

  const loadAlertsData = async () => {
    if (!isAuthenticated) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const [filtersRes, historyRes] = await Promise.all([
        alertsApi.getSavedFilters(),
        alertsApi.getAlertsHistory(25),
      ])
      setFilters(filtersRes || [])
      setHistory(historyRes || [])
    } catch (err) {
      console.error('Error al cargar alertas:', err)
      setError(err.message || 'No se pudieron cargar las alertas')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAlertsData()
  }, [isAuthenticated])

  const handleToggleActive = async (filter) => {
    try {
      const updated = await alertsApi.updateSavedFilter(filter.id, {
        alertas_activas: !filter.alertas_activas,
      })
      setFilters((prev) =>
        prev.map((f) => (f.id === filter.id ? { ...f, alertas_activas: updated.alertas_activas } : f))
      )
    } catch (err) {
      console.error('Error al actualizar estado de alerta:', err)
    }
  }

  const handleToggleFrecuencia = async (filter) => {
    const nextFrec = filter.frecuencia === 'inmediata' ? 'diaria' : 'inmediata'
    try {
      const updated = await alertsApi.updateSavedFilter(filter.id, {
        frecuencia: nextFrec,
      })
      setFilters((prev) =>
        prev.map((f) => (f.id === filter.id ? { ...f, frecuencia: updated.frecuencia } : f))
      )
    } catch (err) {
      console.error('Error al cambiar frecuencia:', err)
    }
  }

  const handleDelete = async (filterId) => {
    if (!window.confirm('¿Está seguro de eliminar esta búsqueda guardada?')) return
    try {
      await alertsApi.deleteSavedFilter(filterId)
      setFilters((prev) => prev.filter((f) => f.id !== filterId))
    } catch (err) {
      console.error('Error al eliminar filtro:', err)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-[1560px] p-4 md:p-6">
        <div className="card grid min-h-[60vh] place-items-center p-8 text-center">
          <div className="max-w-md space-y-4">
            <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-brand-50 text-brand-600">
              <Icon name="bell" className="h-7 w-7" />
            </span>
            <h2 className="text-lg font-bold text-slate-900">Alertas Personalizadas por Correo</h2>
            <p className="text-xs text-slate-500 leading-relaxed">
              Inicia sesión o crea una cuenta gratuita para guardar filtros de búsqueda y recibir alertas automáticas cada vez que se publiquen nuevas contrataciones del SEACE que coincidan con tus rubros.
            </p>
            <div className="pt-2">
              <button onClick={() => openAuthModal('login')} className="btn-primary">
                <Icon name="user" className="h-4 w-4" /> Iniciar Sesión / Registrarse
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[1560px] space-y-5 p-4 md:p-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
            Alertas IA y Búsquedas Guardadas
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Monitoreo proactivo de licitaciones con notificación automática a <strong className="text-slate-800">{user?.email}</strong>.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleSendTestEmail}
            disabled={testEmailStatus === 'sending'}
            className={`btn-ghost text-xs border border-slate-200 transition-all ${
              testEmailStatus === 'success'
                ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                : testEmailStatus === 'error'
                ? 'bg-red-50 text-red-700 border-red-300'
                : 'hover:bg-slate-50 text-slate-700'
            }`}
            title="Envía un correo de prueba a tu email registrado"
          >
            {testEmailStatus === 'sending' ? (
              <>
                <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
                <span>Enviando prueba...</span>
              </>
            ) : testEmailStatus === 'success' ? (
              <>
                <Icon name="check" className="h-3.5 w-3.5 text-emerald-600" />
                <span>¡Correo de prueba enviado!</span>
              </>
            ) : testEmailStatus === 'error' ? (
              <>
                <Icon name="x" className="h-3.5 w-3.5 text-red-600" />
                <span>Error al enviar</span>
              </>
            ) : (
              <>
                <Icon name="bell" className="h-3.5 w-3.5 text-slate-500" />
                <span>Enviar correo de prueba</span>
              </>
            )}
          </button>

          <button
            onClick={() => dispatch({ type: 'SET_VIEW', view: 'dashboard' })}
            className="btn-primary text-xs"
          >
            <Icon name="search" className="h-3.5 w-3.5" /> Explorar y Guardar Nueva Búsqueda
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab('filtros')}
          className={`border-b-2 px-4 py-2 text-xs font-bold transition-colors ${
            activeTab === 'filtros'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Mis Búsquedas Guardadas ({filters.length})
        </button>
        <button
          onClick={() => setActiveTab('historial')}
          className={`border-b-2 px-4 py-2 text-xs font-bold transition-colors ${
            activeTab === 'historial'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Historial de Alertas ({history.length})
        </button>
      </div>

      {loading ? (
        <div className="card p-12 text-center text-slate-400">
          <span className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
          <p className="mt-2 text-xs font-semibold text-slate-600">Cargando tus alertas...</p>
        </div>
      ) : activeTab === 'filtros' ? (
        /* Lista de filtros guardados */
        filters.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filters.map((filter) => {
              const crit = filter.filtros || {}
              return (
                <div
                  key={filter.id}
                  className={`card p-4 flex flex-col justify-between transition-all ${
                    filter.alertas_activas ? 'border-brand-200 ring-1 ring-brand-500/10' : 'opacity-85'
                  }`}
                >
                  <div>
                    {/* Fila superior: Nombre y acciones */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h3 className="text-sm font-bold text-slate-900 truncate" title={filter.nombre}>
                          {filter.nombre}
                        </h3>
                        <span className="text-[10px] text-slate-400">
                          {filter.coincidencias_actuales} oportunidades activas encontradas
                        </span>
                      </div>
                      <button
                        onClick={() => handleDelete(filter.id)}
                        className="icon-btn h-7 w-7 text-slate-400 hover:text-red-600"
                        title="Eliminar búsqueda guardada"
                      >
                        <Icon name="x" className="h-3.5 w-3.5" />
                      </button>
                    </div>

                    {/* Criterios activos */}
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {crit.rubro && <RubroBadge rubro={crit.rubro} />}
                      {crit.tipo && <TipoObjetoBadge tipo={crit.tipo} />}
                      {crit.q && (
                        <span className="chip bg-sky-50 text-sky-700">Texto: "{crit.q}"</span>
                      )}
                      {crit.monto_min && (
                        <span className="chip bg-slate-100 text-slate-700">Mín: {fmtPEN(crit.monto_min)}</span>
                      )}
                      {crit.vigentes && (
                        <span className="chip bg-emerald-50 text-emerald-700">Solo Vigentes</span>
                      )}
                    </div>
                  </div>

                  {/* Controles de alerta al pie */}
                  <div className="mt-4 border-t border-slate-100 pt-3 flex items-center justify-between text-xs">
                    <button
                      onClick={() => handleToggleActive(filter)}
                      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 font-semibold transition-colors ${
                        filter.alertas_activas
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${filter.alertas_activas ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                      {filter.alertas_activas ? 'Alertas Activas' : 'Alertas en Pausa'}
                    </button>

                    <button
                      onClick={() => handleToggleFrecuencia(filter)}
                      className="text-[11px] font-semibold text-slate-500 hover:text-slate-800 flex items-center gap-1"
                      title="Alternar entre notificación inmediata o resumen diario"
                    >
                      {filter.frecuencia === 'inmediata' ? '⚡ Inmediata' : '📅 Diaria'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="card p-12 text-center max-w-lg mx-auto">
            <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-slate-100 text-slate-400">
              <Icon name="bell" className="h-6 w-6" />
            </span>
            <p className="mt-3 text-sm font-bold text-slate-800">Aún no tienes búsquedas guardadas</p>
            <p className="mt-1 text-xs text-slate-500">
              Aplica filtros en el buscador o tabla y haz click en "Guardar búsqueda" para activar el monitoreo automático.
            </p>
            <button
              onClick={() => dispatch({ type: 'SET_VIEW', view: 'dashboard' })}
              className="btn-primary mt-4 text-xs"
            >
              Ir al Buscador de Convocatorias
            </button>
          </div>
        )
      ) : (
        /* Historial de alertas enviadas */
        history.length > 0 ? (
          <div className="card overflow-hidden">
            <div className="overflow-x-auto scroll-thin">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/80 text-[11px] font-bold uppercase text-slate-400">
                    <th className="px-4 py-2.5">Filtro / Regla</th>
                    <th className="px-3 py-2.5">Convocatoria</th>
                    <th className="px-3 py-2.5">Entidad</th>
                    <th className="px-3 py-2.5">Rubro</th>
                    <th className="px-3 py-2.5 text-right">Valor Estimado</th>
                    <th className="px-3 py-2.5">Notificado en</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {history.map((h) => (
                    <tr key={h.alert_id} className="hover:bg-slate-50/80">
                      <td className="px-4 py-3 font-semibold text-brand-700">{h.filtro_nombre}</td>
                      <td className="px-3 py-3">
                        <span className="font-mono font-bold text-slate-800">{h.codigo_seace}</span>
                        <p className="line-clamp-1 max-w-[280px] text-slate-500">{h.objeto}</p>
                      </td>
                      <td className="px-3 py-3 text-slate-700">{h.entidad}</td>
                      <td className="px-3 py-3">
                        <RubroBadge rubro={h.rubro} />
                      </td>
                      <td className="px-3 py-3 text-right font-bold text-slate-900 tabular-nums">
                        {fmtPEN(h.monto_estimado)}
                      </td>
                      <td className="px-3 py-3 text-slate-400 tabular-nums">
                        {h.enviado_en.slice(0, 16).replace('T', ' ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="card p-12 text-center text-slate-400 text-xs">
            Aún no se han enviado alertas automáticas para tus filtros guardados.
          </div>
        )
      )}
    </div>
  )
}

export default AlertsView

