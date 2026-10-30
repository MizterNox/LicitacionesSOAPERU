import { useState, useEffect } from 'react'
import { useApp } from '../../store/AppState.jsx'
import { Icon } from '../ui/Icon.jsx'
import { adminApi } from '../../lib/api.js'

const TIPOS_INFO = {
  Servicios: {
    label: 'Servicios',
    sub: 'Consultorías en general, servicios de mantenimiento, asesorías y supervisión técnica.',
    icon: 'briefcase',
    color: 'from-blue-500 to-indigo-600',
    borderActive: 'border-blue-500/50 bg-blue-50/40',
  },
  Bienes: {
    label: 'Bienes',
    sub: 'Suministro de materiales, adquisición de equipos, insumos médicos y compras públicas.',
    icon: 'box',
    color: 'from-amber-500 to-orange-600',
    borderActive: 'border-amber-500/50 bg-amber-50/40',
  },
  Obras: {
    label: 'Obras',
    sub: 'Construcción civil, infraestructura vial, remodelación y edificaciones públicas.',
    icon: 'hammer',
    color: 'from-emerald-500 to-teal-600',
    borderActive: 'border-emerald-500/50 bg-emerald-50/40',
  },
}

export default function ConfigView() {
  const { state, dispatch } = useApp()
  const [activeTab, setActiveTab] = useState('preferencias') // 'preferencias' | 'admin'
  const [tipos, setTipos] = useState(['Servicios', 'Bienes', 'Obras'])
  const [savingTipos, setSavingTipos] = useState(false)
  const [saveMessage, setSaveMessage] = useState(null)

  // Opciones de sincronización manual para administradores
  const [syncDays, setSyncDays] = useState(7)
  const [syncPages, setSyncPages] = useState(2)
  const [syncTarget, setSyncTarget] = useState('todos') // 'todos' o tipo específico
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncFeedback, setSyncFeedback] = useState(null)

  const [cronStatus, setCronStatus] = useState(null)
  const [cronHistory, setCronHistory] = useState([])
  const [loadingData, setLoadingData] = useState(true)

  const fetchConfigAndHistory = async () => {
    try {
      // 1. Cargar tipos activos
      const dataTipos = await adminApi.getTiposConfig().catch(() => null)
      if (dataTipos?.tipos_activos) {
        setTipos(dataTipos.tipos_activos)
        dispatch({ type: 'SET_TIPOS_CONFIG', payload: dataTipos.tipos_activos })
      }

      // 2. Cargar estado de cron
      const dataStatus = await adminApi.getCronStatus().catch(() => null)
      if (dataStatus) {
        setCronStatus(dataStatus)
        dispatch({ type: 'SET_CRON_STATUS', payload: dataStatus })
      }

      // 3. Cargar historial de ejecuciones
      const dataHist = await adminApi.getCronHistory(15).catch(() => null)
      if (Array.isArray(dataHist)) setCronHistory(dataHist)
    } catch (err) {
      console.error('Error al cargar datos de configuración:', err)
    } finally {
      setLoadingData(false)
    }
  }

  useEffect(() => {
    fetchConfigAndHistory()
  }, [])

  const handleToggleTipo = (t) => {
    setTipos((prev) => {
      if (prev.includes(t)) {
        if (prev.length === 1) return prev // Mantener al menos 1 tipo activo
        return prev.filter((item) => item !== t)
      } else {
        return [...prev, t]
      }
    })
    setSaveMessage(null)
  }

  const handleSaveTipos = async () => {
    setSavingTipos(true)
    setSaveMessage(null)
    try {
      const data = await adminApi.saveTiposConfig(tipos)
      dispatch({ type: 'SET_TIPOS_CONFIG', payload: data.tipos_activos })
      setSaveMessage({ type: 'success', text: 'Preferencias guardadas exitosamente' })
      fetchConfigAndHistory()
    } catch (err) {
      setSaveMessage({ type: 'error', text: err.message })
    } finally {
      setSavingTipos(false)
    }
  }

  const handleTriggerManualSync = async () => {
    setIsSyncing(true)
    setSyncFeedback(null)
    try {
      const targets = syncTarget === 'todos' ? (tipos.length ? tipos : ['Servicios', 'Bienes']) : [syncTarget]
      let totalNuevos = 0
      let totalIgnorados = 0

      for (const t of targets) {
        const data = await adminApi.triggerEtl({
          objeto: t,
          estado: 'Vigente',
          dias_atras: Number(syncDays),
          max_pages: Number(syncPages),
        })
        const r = data?.resultado || {}
        totalNuevos += r.total_guardados_db || 0
        totalIgnorados += r.total_ignorados || 0
      }

      setSyncFeedback({
        type: 'success',
        text: `Sincronización finalizada con éxito: +${totalNuevos} convocatorias registradas (${totalIgnorados} ya existían y se preservaron intactas).`,
      })
      await fetchConfigAndHistory()
    } catch (err) {
      setSyncFeedback({ type: 'error', text: err.message || 'Error durante la sincronización' })
    } finally {
      setIsSyncing(false)
    }
  }

  const lastExec = cronStatus?.ultima_ejecucion

  return (
    <div className="mx-auto max-w-[1400px] space-y-5 p-4 md:p-6">
      {/* Encabezado Principal */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-50 text-brand-600">
              <Icon name="settings" className="h-4 w-4" />
            </span>
            Configuración del Sistema
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Personaliza tus rubros prioritarios de licitación y supervisa las sincronizaciones oficiales con el SEACE.
          </p>
        </div>
        <button
          onClick={() => dispatch({ type: 'SET_VIEW', view: 'dashboard' })}
          className="btn-secondary self-start sm:self-auto text-xs"
        >
          <Icon name="layout-dashboard" className="h-3.5 w-3.5" /> Volver al Dashboard
        </button>
      </div>

      {/* Selector de Pestañas (Tabs) */}
      <div className="flex border-b border-slate-200">
        <button
          type="button"
          onClick={() => setActiveTab('preferencias')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-colors ${
            activeTab === 'preferencias'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Icon name="sliders" className="h-4 w-4" />
          Preferencias de Búsqueda
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('admin')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-colors ${
            activeTab === 'admin'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Icon name="clock" className="h-4 w-4" />
          Sincronización y Auditoría SEACE
          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">
            Admin
          </span>
        </button>
      </div>

      {/* PESTAÑA 1: PREFERENCIAS DE USUARIO */}
      {activeTab === 'preferencias' && (
        <div className="space-y-5">
          <div className="card p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-sm font-bold text-slate-900">
                  Rubros de Contratación de Interés
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Selecciona los sectores en los que tu empresa participa habitualmente en contrataciones públicas.
                </p>
              </div>
              <span className="chip bg-brand-50 text-brand-700 font-bold">
                {tipos.length} de 3 habilitados
              </span>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {Object.entries(TIPOS_INFO).map(([key, info]) => {
                const active = tipos.includes(key)
                return (
                  <div
                    key={key}
                    onClick={() => handleToggleTipo(key)}
                    className={`group relative flex flex-col justify-between rounded-xl border p-4 cursor-pointer transition-all duration-200 ${
                      active
                        ? `${info.borderActive} shadow-sm ring-1 ring-brand-500/20`
                        : 'border-slate-200 bg-white hover:border-slate-300 opacity-70'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <span className={`grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br ${info.color} text-white shadow-sm`}>
                        <Icon name={info.icon} className="h-4 w-4" />
                      </span>
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-500'
                        }`}
                      >
                        {active ? 'Activo' : 'Inactivo'}
                      </span>
                    </div>

                    <div className="mt-3">
                      <h3 className="text-sm font-bold text-slate-800">{info.label}</h3>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{info.sub}</p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-100/80 flex items-center justify-between text-[11px] font-semibold text-slate-600">
                      <span>Monitorear oportunidades</span>
                      <input
                        type="checkbox"
                        checked={active}
                        onChange={() => handleToggleTipo(key)}
                        onClick={(e) => e.stopPropagation()}
                        className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                      />
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="flex flex-col gap-2 pt-2 sm:flex-row sm:items-center sm:justify-between">
              <span className="text-[11px] text-slate-400">
                Los procesos automáticos de actualización darán prioridad a las categorías que mantengas activas.
              </span>
              <div className="flex items-center gap-2">
                {saveMessage && (
                  <span
                    className={`text-xs font-semibold ${
                      saveMessage.type === 'success' ? 'text-emerald-600' : 'text-red-600'
                    }`}
                  >
                    {saveMessage.text}
                  </span>
                )}
                <button
                  type="button"
                  onClick={handleSaveTipos}
                  disabled={savingTipos}
                  className="btn-primary text-xs"
                >
                  <Icon name="check" className="h-3.5 w-3.5" />
                  {savingTipos ? 'Guardando...' : 'Guardar Preferencias'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* PESTAÑA 2: ADMINISTRACIÓN & AUDITORÍA SEACE */}
      {activeTab === 'admin' && (
        <div className="space-y-5">
          {/* Fila de Controles: Formulario de Sincronización + Estado del Planificador */}
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
            {/* Panel de Sincronización Manual Avanzada (2 cols) */}
            <div className="card p-5 lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Icon name="sparkles" className="h-4 w-4 text-brand-600" />
                    Sincronización Manual con SEACE
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Descarga oportunidades vigentes directamente desde la API oficial de Contrataciones Abiertas de Perú.
                  </p>
                </div>
                <span className="chip bg-brand-50 text-brand-700 font-semibold text-[11px]">
                  Carga Incremental Segura
                </span>
              </div>

              {/* Parámetros de Extracción */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div>
                  <label className="field-label mb-1">Rango de Días</label>
                  <select
                    value={syncDays}
                    onChange={(e) => setSyncDays(Number(e.target.value))}
                    className="field h-9 text-xs font-medium"
                  >
                    <option value={7}>Últimos 7 días (Recomendado)</option>
                    <option value={0}>Solo hoy (Publicaciones del día)</option>
                    <option value={15}>Últimos 15 días</option>
                    <option value={30}>Últimos 30 días</option>
                  </select>
                </div>

                <div>
                  <label className="field-label mb-1">Volumen / Páginas</label>
                  <select
                    value={syncPages}
                    onChange={(e) => setSyncPages(Number(e.target.value))}
                    className="field h-9 text-xs font-medium"
                  >
                    <option value={2}>2 páginas (~40 convocatorias)</option>
                    <option value={1}>1 página (~20 convocatorias)</option>
                    <option value={4}>4 páginas (~80 convocatorias)</option>
                  </select>
                </div>

                <div>
                  <label className="field-label mb-1">Objeto Contractual</label>
                  <select
                    value={syncTarget}
                    onChange={(e) => setSyncTarget(e.target.value)}
                    className="field h-9 text-xs font-medium"
                  >
                    <option value="todos">Todos los rubros activos</option>
                    <option value="Servicios">Solo Servicios</option>
                    <option value="Bienes">Solo Bienes</option>
                    <option value="Obras">Solo Obras</option>
                  </select>
                </div>
              </div>

              {syncFeedback && (
                <div
                  className={`rounded-lg p-2.5 text-xs font-semibold ${
                    syncFeedback.type === 'success'
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      : 'bg-red-50 text-red-800 border border-red-200'
                  }`}
                >
                  {syncFeedback.text}
                </div>
              )}

              <div className="pt-2 flex items-center justify-between border-t border-slate-100">
                <span className="text-[11px] text-slate-400">
                  Las licitaciones existentes sin cambios se mantendrán intactas de forma automática.
                </span>
                <button
                  type="button"
                  onClick={handleTriggerManualSync}
                  disabled={isSyncing}
                  className="btn-primary text-xs"
                >
                  <Icon name="sparkles" className={`h-3.5 w-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
                  {isSyncing ? 'Sincronizando con SEACE...' : 'Iniciar Sincronización Ahora'}
                </button>
              </div>
            </div>

            {/* Panel de Estado del Planificador Automático */}
            <div className="card p-5 space-y-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Icon name="clock" className="h-4 w-4 text-emerald-600" />
                    Actualización Automática
                  </h2>
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                    Activo
                  </span>
                </div>

                <div className="mt-3 space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">Horarios diarios:</span>
                    <span className="font-semibold text-slate-800">14:00 PM y 02:00 AM</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">Protección de datos:</span>
                    <span className="font-semibold text-emerald-700">Sin sobreescrituras</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Última ejecución:</span>
                    <span className="font-bold text-slate-900">
                      {lastExec?.iniciado_en
                        ? new Date(lastExec.iniciado_en).toLocaleString('es-PE', {
                            day: '2-digit',
                            month: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : 'En espera'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="rounded-lg bg-slate-50 p-2.5 text-[11px] text-slate-500 leading-relaxed border border-slate-100">
                El sistema consolida las publicaciones del día y de la noche de manera autónoma sin requerir intervención manual.
              </div>
            </div>
          </div>

          {/* Bitácora de Auditoría Histórica */}
          <div className="card p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Icon name="file-text" className="h-4 w-4 text-brand-600" />
                  Bitácora de Sincronizaciones del Sistema
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Registro de auditoría y trazabilidad de cada consulta a los servidores del Estado.
                </p>
              </div>
              <button
                onClick={fetchConfigAndHistory}
                className="btn-ghost h-8 text-xs px-2.5"
                title="Actualizar tabla"
              >
                Refrescar
              </button>
            </div>

            {cronHistory.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400">
                No se han registrado ejecuciones previas de sincronización.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      <th className="py-2.5 px-3">Fecha y Hora</th>
                      <th className="py-2.5 px-3">Modalidad</th>
                      <th className="py-2.5 px-3">Estado</th>
                      <th className="py-2.5 px-3">Rubros</th>
                      <th className="py-2.5 px-3 text-right">Extraídas SEACE</th>
                      <th className="py-2.5 px-3 text-right">Nuevas Registradas</th>
                      <th className="py-2.5 px-3 text-right">Preservadas (Sin cambios)</th>
                      <th className="py-2.5 px-3 text-right">Duración</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                    {cronHistory.map((item) => {
                      const d = new Date(item.iniciado_en)
                      const fStr = d.toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' })
                      const hStr = d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                      const isOk = item.estado === 'COMPLETED'
                      return (
                        <tr key={item.id} className="hover:bg-slate-50/70 transition-colors">
                          <td className="py-2.5 px-3 whitespace-nowrap">
                            <span className="font-bold text-slate-900">{fStr}</span>
                            <span className="text-slate-400 ml-1.5">{hStr}</span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                                item.tipo_ejecucion === 'AUTOMATICO'
                                  ? 'bg-blue-50 text-blue-700'
                                  : 'bg-purple-50 text-purple-700'
                              }`}
                            >
                              {item.tipo_ejecucion === 'AUTOMATICO' ? 'Automática' : 'Manual'}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                isOk
                                  ? 'bg-emerald-50 text-emerald-700'
                                  : item.estado === 'RUNNING'
                                  ? 'bg-amber-50 text-amber-700 animate-pulse'
                                  : 'bg-red-50 text-red-700'
                              }`}
                            >
                              <span
                                className={`h-1.5 w-1.5 rounded-full ${
                                  isOk ? 'bg-emerald-500' : item.estado === 'RUNNING' ? 'bg-amber-500' : 'bg-red-500'
                                }`}
                              ></span>
                              {isOk ? 'Completado' : item.estado}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="flex flex-wrap gap-1">
                              {(item.objetos_procesados || []).map((obj) => (
                                <span key={obj} className="chip bg-slate-100 text-slate-600 text-[10px]">
                                  {obj}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="py-2.5 px-3 text-right font-semibold text-slate-800">
                            {item.total_extraidos}
                          </td>
                          <td className="py-2.5 px-3 text-right font-bold text-emerald-700">
                            +{item.total_guardados}
                          </td>
                          <td className="py-2.5 px-3 text-right font-medium text-slate-500">
                            {item.total_ignorados}
                          </td>
                          <td className="py-2.5 px-3 text-right text-slate-500">
                            {item.duracion_segundos != null ? `${item.duracion_segundos}s` : '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
