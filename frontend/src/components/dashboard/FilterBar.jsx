// Filtros colapsables — conectados reactivamente con PostgreSQL y FastAPI.
// Cada control es "controlado": value ← state, onChange → dispatch(SET_FILTER).

import { useMemo } from 'react'
import { useApp } from '../../store/AppState.jsx'
import { Icon } from '../ui/Icon.jsx'

const TIPOS = ['Todos', 'LP', 'CP', 'MS', 'AS', 'MC']
const PLAZOS = [
  ['todas', 'Cualquier plazo'],
  ['48h', 'Menos de 48 h'],
  ['7d', 'Próximos 7 días'],
  ['30d', 'Próximos 30 días'],
]

function Chevron() {
  return <Icon name="chevron-down" className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
}

export default function FilterBar() {
  const { state, dispatch } = useApp()
  const f = state.filters
  const convocatorias = state.convocatorias || []
  const set = (key, value) => dispatch({ type: 'SET_FILTER', key, value })

  const entities = useMemo(() => {
    const s = new Set(convocatorias.map((c) => c.entidad).filter(Boolean))
    return Array.from(s).sort()
  }, [convocatorias])

  const regions = useMemo(() => {
    const s = new Set(convocatorias.map((c) => c.region).filter(Boolean))
    return Array.from(s).sort()
  }, [convocatorias])

  const active =
    (f.tipo !== 'Todos' ? 1 : 0) +
    (f.entidad !== 'todas' ? 1 : 0) +
    (f.region !== 'todas' ? 1 : 0) +
    (f.estado !== 'todos' ? 1 : 0) +
    (f.tipoObjeto !== 'todos' ? 1 : 0) +
    (f.valorMin !== '' ? 1 : 0) +
    (f.valorMax !== '' ? 1 : 0) +
    (f.plazo !== 'todas' ? 1 : 0) +
    (f.fecha !== 'todos' ? 1 : 0)

  return (
    <section className="card overflow-hidden" aria-label="Filtros de búsqueda">
      <div className="flex items-center gap-3 px-4 py-2.5">
        <span className="flex items-center gap-2 text-[13px] font-bold text-slate-700">
          <Icon name="sliders" className="h-4 w-4 text-brand-600" /> Filtros
          {active ? <span className="chip bg-brand-50 text-brand-700">{active} activo{active > 1 ? 's' : ''}</span> : null}
          {state.isLoading && <span className="text-xs text-brand-600 animate-pulse font-medium">· Actualizando desde PostgreSQL...</span>}
        </span>
        <div className="ml-auto flex items-center gap-1">
          <button onClick={() => dispatch({ type: 'CLEAR_FILTERS' })} className="btn-ghost h-8 px-2.5 text-xs">
            Limpiar
          </button>
          <button
            onClick={() => dispatch({ type: 'TOGGLE_FILTERS' })}
            className="icon-btn h-8 w-8"
            title={state.filtersOpen ? 'Plegar filtros' : 'Expandir filtros'}
          >
            <Icon name="chevron-down" className={`h-4 w-4 transition-transform duration-200 ${state.filtersOpen ? 'rotate-180' : ''}`} />
          </button>
        </div>
      </div>

      {state.filtersOpen && (
        <div className="border-t border-slate-100 bg-slate-50/70 p-3.5">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {/* Tipo de objeto (enum: Bienes / Servicios / Obras) */}
            <div>
              <label htmlFor="f-tipo-objeto" className="field-label">Objeto Contractual</label>
              <div className="relative">
                <select id="f-tipo-objeto" value={f.tipoObjeto} onChange={(e) => set('tipoObjeto', e.target.value)} className="field appearance-none pr-8 font-medium">
                  <option value="todos">Todos los Objetos</option>
                  <option value="Bienes">Bienes</option>
                  <option value="Servicios">Servicios</option>
                  <option value="Obras">Obras</option>
                </select>
                <Chevron />
              </div>
            </div>

            {/* Estado (Vigente / Finalizado / Todos) */}
            <div>
              <label htmlFor="f-estado" className="field-label">Estado de Convocatoria</label>
              <div className="relative">
                <select id="f-estado" value={f.estado} onChange={(e) => set('estado', e.target.value)} className="field appearance-none pr-8 font-medium">
                  <option value="Vigente">Solo Vigentes (Activas)</option>
                  <option value="todos">Todos los Estados</option>
                  <option value="Finalizado">Finalizados</option>
                </select>
                <Chevron />
              </div>
            </div>

            {/* Fecha de publicación (Hoy vs Todos) */}
            <div>
              <label htmlFor="f-fecha" className="field-label">Fecha de Publicación</label>
              <div className="relative">
                <select id="f-fecha" value={f.fecha || 'hoy'} onChange={(e) => set('fecha', e.target.value)} className="field appearance-none pr-8 font-medium">
                  <option value="hoy">Publicados Hoy (Día actual)</option>
                  <option value="todos">Todos los Registros</option>
                </select>
                <Chevron />
              </div>
            </div>

            {/* Tipo de proceso (LP, CP, AS...) */}
            <div>
              <span className="field-label">Tipo de Proceso</span>
              <div className="flex h-9 items-center gap-1 rounded-lg border border-slate-200 bg-white p-1">
                {TIPOS.map((t) => (
                  <button
                    key={t}
                    onClick={() => set('tipo', t)}
                    className={`h-7 flex-1 rounded-md text-xs font-bold transition-colors ${
                      f.tipo === t ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-500 hover:bg-slate-100'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            {/* Entidad compradora */}
            <div>
              <label htmlFor="f-entidad" className="field-label">Entidad Compradora</label>
              <div className="relative">
                <select id="f-entidad" value={f.entidad} onChange={(e) => set('entidad', e.target.value)} className="field appearance-none pr-8">
                  <option value="todas">Todas las Entidades</option>
                  {entities.map((ent) => (
                    <option key={ent} value={ent}>{ent}</option>
                  ))}
                </select>
                <Chevron />
              </div>
            </div>

            {/* Región */}
            <div>
              <label htmlFor="f-region" className="field-label">Región</label>
              <div className="relative">
                <select id="f-region" value={f.region} onChange={(e) => set('region', e.target.value)} className="field appearance-none pr-8">
                  <option value="todas">Todas las Regiones</option>
                  {regions.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
                <Chevron />
              </div>
            </div>

            {/* Rango de valor estimado */}
            <div>
              <span className="field-label">Valor Estimado (S/)</span>
              <div className="flex items-center gap-1.5">
                <div className="relative flex-1">
                  <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[11px] font-bold text-slate-400">S/</span>
                  <input type="number" min="0" placeholder="Min" value={f.valorMin} onChange={(e) => set('valorMin', e.target.value)} className="field h-9 pl-7 text-xs" />
                </div>
                <span className="text-slate-300">–</span>
                <div className="relative flex-1">
                  <input type="number" min="0" placeholder="Máx" value={f.valorMax} onChange={(e) => set('valorMax', e.target.value)} className="field h-9 text-xs" />
                </div>
              </div>
            </div>

            {/* Plazo / Fecha límite */}
            <div>
              <label htmlFor="f-plazo" className="field-label">Plazo de Ofertas</label>
              <div className="relative">
                <select id="f-plazo" value={f.plazo} onChange={(e) => set('plazo', e.target.value)} className="field appearance-none pr-8">
                  {PLAZOS.map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </select>
                <Chevron />
              </div>
            </div>

          </div>
          <div className="mt-3 flex items-center justify-between border-t border-slate-200/60 pt-2 text-[11px] text-slate-400">
            <span>Conectado en tiempo real a PostgreSQL (<span className="font-semibold text-slate-600">licitacionesELT</span>) vía FastAPI.</span>
            <span>{convocatorias.length} procesos cargados</span>
          </div>
        </div>
      )}
    </section>
  )
}
