import { useState, useRef, useEffect } from 'react'
import { useApp } from '../../store/AppState.jsx'
import { downloadExport } from '../../lib/api.js'
import { Icon } from '../ui/Icon.jsx'

export function ExportMenu() {
  const { state } = useApp()
  const [isOpen, setIsOpen] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [currentFormat, setCurrentFormat] = useState(null)
  const [errorMsg, setErrorMsg] = useState(null)
  const menuRef = useRef(null)

  // Cerrar al hacer click fuera o presionar Escape
  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }
    function handleKeyDown(e) {
      if (e.key === 'Escape') setIsOpen(false)
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      document.addEventListener('keydown', handleKeyDown)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  // Construir mapa de filtros activos
  const buildCurrentFilters = () => {
    const f = state.filters || {}
    const params = {}

    if (f.estado === 'Vigente') {
      params.vigentes = true
    } else if (f.estado === 'Finalizado') {
      params.vigentes = false
    }

    if (f.tipoObjeto && f.tipoObjeto !== 'todos') {
      params.tipo = f.tipoObjeto
    }

    if (f.rubro && f.rubro !== 'todos') {
      params.rubro = f.rubro
    }

    if (f.fecha && f.fecha !== 'todos') {
      params.fecha = f.fecha
    }

    if (state.query && state.query.trim()) {
      params.q = state.query.trim()
    }

    if (f.valorMin) {
      params.monto_min = f.valorMin
    }
    if (f.valorMax) {
      params.monto_max = f.valorMax
    }

    if (state.sort) {
      params.sort = state.sort === 'match' ? 'relevance' : state.sort
    }

    return params
  }

  const handleExport = async (format) => {
    setIsExporting(true)
    setCurrentFormat(format)
    setErrorMsg(null)
    setIsOpen(false)

    try {
      const filters = buildCurrentFilters()
      await downloadExport(format, filters)
    } catch (err) {
      console.error('Error al exportar:', err)
      setErrorMsg(err.message || 'Error al generar la descarga')
      setTimeout(() => setErrorMsg(null), 4000)
    } finally {
      setIsExporting(false)
      setCurrentFormat(null)
    }
  };

  return (
    <div className="relative inline-block text-left" ref={menuRef}>
      {/* Botón principal */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isExporting}
        className={`inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition-all hover:border-slate-300 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-500/20 active:scale-95 disabled:pointer-events-none disabled:opacity-60 ${
          isOpen ? 'border-brand-500 ring-2 ring-brand-500/10' : ''
        }`}
        title="Exportar convocatorias filtradas"
        id="btn-export-menu"
      >
        {isExporting ? (
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
        ) : (
          <Icon name="download" className="h-3.5 w-3.5 text-slate-500" />
        )}
        <span className="hidden sm:inline">
          {isExporting ? `Generando ${currentFormat?.toUpperCase()}...` : 'Exportar'}
        </span>
        <Icon
          name="chevron-down"
          className={`h-3 w-3 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Menú desplegable */}
      {isOpen && (
        <div className="absolute right-0 z-30 mt-1.5 w-72 origin-top-right rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl ring-1 ring-black/5 animate-in fade-in zoom-in-95 duration-100">
          <div className="px-2.5 py-2 border-b border-slate-100">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Exportar vista actual</p>
            <p className="text-xs text-slate-500 mt-0.5">
              Descarga con los filtros y búsquedas aplicadas.
            </p>
          </div>

          <div className="py-1">
            {/* Opción CSV */}
            <button
              onClick={() => handleExport('csv')}
              className="group flex w-full items-start gap-2.5 rounded-lg p-2 text-left hover:bg-slate-50 transition-colors"
              id="btn-export-csv"
            >
              <span className="mt-0.5 grid h-7 w-7 flex-shrink-0 place-items-center rounded-md bg-emerald-50 text-emerald-600 group-hover:bg-emerald-100">
                <Icon name="file-text" className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold text-slate-800">Archivo CSV (.csv)</span>
                  <span className="rounded bg-emerald-100 px-1 py-0.2 text-[9px] font-bold text-emerald-800">Excel / Sheets</span>
                </div>
                <p className="text-[11px] text-slate-500 leading-tight mt-0.5">
                  UTF-8 con BOM y delimitador (;). Abre nativamente en Excel sin caracteres rotos.
                </p>
              </div>
            </button>

            {/* Opción XLSX */}
            <button
              onClick={() => handleExport('xlsx')}
              className="group flex w-full items-start gap-2.5 rounded-lg p-2 text-left hover:bg-slate-50 transition-colors"
              id="btn-export-xlsx"
            >
              <span className="mt-0.5 grid h-7 w-7 flex-shrink-0 place-items-center rounded-md bg-teal-50 text-teal-600 group-hover:bg-teal-100">
                <Icon name="table" className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold text-slate-800">Microsoft Excel (.xlsx)</span>
                  <span className="rounded bg-teal-100 px-1 py-0.2 text-[9px] font-bold text-teal-800">Formato Pro</span>
                </div>
                <p className="text-[11px] text-slate-500 leading-tight mt-0.5">
                  Libro con formato, cabecera oscura, montos numéricos en S/ y filtros de columna.
                </p>
              </div>
            </button>
          </div>
        </div>
      )}

      {/* Toast de error si falla */}
      {errorMsg && (
        <div className="absolute right-0 top-full mt-2 z-40 rounded-lg bg-red-600 px-3 py-1.5 text-xs text-white shadow-lg">
          {errorMsg}
        </div>
      )}
    </div>
  )
}
