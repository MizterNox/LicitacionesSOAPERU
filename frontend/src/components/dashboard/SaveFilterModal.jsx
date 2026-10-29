import { useState } from 'react'
import { alertsApi } from '../../lib/api.js'
import { useAuth } from '../../store/AuthContext.jsx'
import { Icon } from '../ui/Icon.jsx'

export function SaveFilterModal({ isOpen, onClose, currentFilters, query, onSaved }) {
  const { user } = useAuth()
  const [nombre, setNombre] = useState('')
  const [alertasActivas, setAlertasActivas] = useState(true)
  const [frecuencia, setFrecuencia] = useState('inmediata')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  if (!isOpen) return null

  // Construir nombre por defecto sugerido
  const defaultNombre = () => {
    if (currentFilters.rubro && currentFilters.rubro !== 'todos') {
      return `Licitaciones de ${currentFilters.rubro}`
    }
    if (query && query.trim()) {
      return `Búsqueda: ${query.trim()}`
    }
    if (currentFilters.tipoObjeto && currentFilters.tipoObjeto !== 'todos') {
      return `Contrataciones de ${currentFilters.tipoObjeto}`
    }
    return 'Mi Filtro de Licitaciones'
  }

  const handleSave = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const finalName = (nombre || defaultNombre()).trim()

    // Preparar objeto de filtros serializables
    const payloadFilters = {}
    if (currentFilters.estado === 'Vigente') payloadFilters.vigentes = true
    else if (currentFilters.estado === 'Finalizado') payloadFilters.vigentes = false

    if (currentFilters.tipoObjeto && currentFilters.tipoObjeto !== 'todos') {
      payloadFilters.tipo = currentFilters.tipoObjeto
    }
    if (currentFilters.rubro && currentFilters.rubro !== 'todos') {
      payloadFilters.rubro = currentFilters.rubro
    }
    if (currentFilters.region && currentFilters.region !== 'todas') {
      payloadFilters.region = currentFilters.region
    }
    if (currentFilters.valorMin) {
      payloadFilters.monto_min = Number(currentFilters.valorMin)
    }
    if (currentFilters.valorMax) {
      payloadFilters.monto_max = Number(currentFilters.valorMax)
    }
    if (query && query.trim()) {
      payloadFilters.q = query.trim()
    }

    try {
      const res = await alertsApi.createSavedFilter({
        nombre: finalName,
        filtros: payloadFilters,
        alertas_activas: alertasActivas,
        frecuencia,
      })
      setSuccess(true)
      if (onSaved) onSaved(res)
      setTimeout(() => {
        setSuccess(false)
        onClose()
      }, 1500)
    } catch (err) {
      console.error('Error al guardar filtro:', err)
      setError(err.message || 'No se pudo guardar el filtro.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm"
        onClick={onClose}
      />

      <div className="relative w-full max-w-md overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/60 px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-amber-50 text-amber-600">
              <Icon name="bell" className="h-4 w-4" />
            </span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Guardar Búsqueda y Crear Alerta</h3>
              <p className="text-[10px] text-slate-400">Notificaciones automáticas post-ETL</p>
            </div>
          </div>
          <button onClick={onClose} className="icon-btn h-8 w-8 text-slate-400 hover:text-slate-700">
            <Icon name="x" className="h-4 w-4" />
          </button>
        </div>

        {success ? (
          <div className="p-8 text-center space-y-2">
            <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-emerald-50 text-emerald-600">
              <Icon name="check" className="h-6 w-6" />
            </span>
            <p className="text-sm font-bold text-slate-900">¡Búsqueda guardada con éxito!</p>
            <p className="text-xs text-slate-500">
              Recibirás alertas en <strong className="text-slate-800">{user?.email}</strong> cada vez que ingresen nuevas oportunidades.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSave} className="p-5 space-y-4">
            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
                {error}
              </div>
            )}

            <div>
              <label className="field-label mb-1">Nombre de la Búsqueda Guardada</label>
              <input
                type="text"
                required
                placeholder={defaultNombre()}
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                className="field h-9 text-xs font-medium"
              />
            </div>

            {/* Resumen de criterios */}
            <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-3 text-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
                Criterios que se guardarán:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {currentFilters.rubro && currentFilters.rubro !== 'todos' && (
                  <span className="chip bg-indigo-50 text-indigo-700">Rubro: {currentFilters.rubro}</span>
                )}
                {currentFilters.tipoObjeto && currentFilters.tipoObjeto !== 'todos' && (
                  <span className="chip bg-brand-50 text-brand-700">Tipo: {currentFilters.tipoObjeto}</span>
                )}
                {query && query.trim() && (
                  <span className="chip bg-sky-50 text-sky-700">Texto: "{query.trim()}"</span>
                )}
                {currentFilters.estado && currentFilters.estado !== 'todos' && (
                  <span className="chip bg-emerald-50 text-emerald-700">Estado: {currentFilters.estado}</span>
                )}
                {currentFilters.valorMin && (
                  <span className="chip bg-slate-100 text-slate-700">Mín: S/ {Number(currentFilters.valorMin).toLocaleString()}</span>
                )}
              </div>
            </div>

            {/* Interruptor de alertas */}
            <div className="flex items-center justify-between rounded-xl border border-slate-200 p-3">
              <div>
                <p className="text-xs font-bold text-slate-800">Alertas por Correo Electrónico</p>
                <p className="text-[11px] text-slate-500">Enviar email cuando el cron detecte nuevas compras públicas</p>
              </div>
              <input
                type="checkbox"
                checked={alertasActivas}
                onChange={(e) => setAlertasActivas(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              />
            </div>

            {/* Frecuencia de envío */}
            {alertasActivas && (
              <div>
                <label className="field-label mb-1">Frecuencia de Notificación</label>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <label
                    className={`flex items-center gap-2 rounded-lg border p-2.5 cursor-pointer transition-all ${
                      frecuencia === 'inmediata'
                        ? 'border-brand-500 bg-brand-50/50 font-bold text-brand-900'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="frecuencia"
                      value="inmediata"
                      checked={frecuencia === 'inmediata'}
                      onChange={() => setFrecuencia('inmediata')}
                      className="sr-only"
                    />
                    <span>⚡ En tiempo real (post-ETL)</span>
                  </label>

                  <label
                    className={`flex items-center gap-2 rounded-lg border p-2.5 cursor-pointer transition-all ${
                      frecuencia === 'diaria'
                        ? 'border-brand-500 bg-brand-50/50 font-bold text-brand-900'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="frecuencia"
                      value="diaria"
                      checked={frecuencia === 'diaria'}
                      onChange={() => setFrecuencia('diaria')}
                      className="sr-only"
                    />
                    <span>📅 Resumen Diario</span>
                  </label>
                </div>
              </div>
            )}

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full h-9.5 text-xs font-bold justify-center shadow-md active:scale-[0.99] disabled:opacity-60"
              >
                {loading ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  'Guardar filtro y activar alertas'
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
