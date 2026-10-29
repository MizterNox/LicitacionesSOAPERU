// Selectores: filtrado + ordenamiento sobre los datos reales en state.convocatorias.

import { useMemo } from 'react'
import { useApp } from './AppState.jsx'
import { daysUntil } from '../utils/format.js'

export function selectVisible(state) {
  const f = state.filters
  const listData = state.convocatorias || []

  let list = listData.filter((c) => {
    if (f.soloMenores && !c.es_menor_cuantia) return false
    if (f.tipo !== 'Todos' && c.tipo_proceso !== f.tipo) return false
    if (f.entidad !== 'todas' && c.entidad !== f.entidad) return false
    if (f.region !== 'todas' && c.region !== f.region) return false
    if (f.estado !== 'todos' && c.estado !== f.estado) return false
    if (f.tipoObjeto !== 'todos' && c.tipo_objeto !== f.tipoObjeto) return false
    if (f.rubro && f.rubro !== 'todos' && c.rubro !== f.rubro) return false
    if (f.valorMin !== '' && (c.valor_estimado ?? 0) < Number(f.valorMin)) return false
    if (f.valorMax !== '' && c.valor_estimado != null && c.valor_estimado > Number(f.valorMax)) return false
    if (f.plazo !== 'todas') {
      const dl = c.fecha_limite ? daysUntil(c.fecha_limite) : null
      if (dl == null || dl < 0) return false
      const lim = f.plazo === '48h' ? 2 : f.plazo === '7d' ? 7 : 30
      if (dl > lim) return false
    }
    return true
  })

  list = [...list].sort((a, b) => {
    if (state.sort === 'date') {
      const da = a.fecha_publicacion ? new Date(a.fecha_publicacion).getTime() : 0
      const db = b.fecha_publicacion ? new Date(b.fecha_publicacion).getTime() : 0
      return db - da
    }
    if (state.sort === 'value') return (b.valor_estimado ?? -1) - (a.valor_estimado ?? -1)
    if (state.sort === 'deadline') {
      const da = a.fecha_limite ? daysUntil(a.fecha_limite) : 9999
      const db = b.fecha_limite ? daysUntil(b.fecha_limite) : 9999
      return da - db
    }
    if (state.sort === 'match') {
      return (b.match_score ?? 0) - (a.match_score ?? 0)
    }
    const da = a.fecha_publicacion ? new Date(a.fecha_publicacion).getTime() : 0
    const db = b.fecha_publicacion ? new Date(b.fecha_publicacion).getTime() : 0
    return db - da
  })

  return list
}

export function useVisibleConvocatorias() {
  const { state } = useApp()
  return useMemo(
    () => selectVisible(state),
    [state.convocatorias, state.query, state.filters, state.sort]
  )
}

export function useSelectedConvocatoria() {
  const { state } = useApp()
  return useMemo(() => {
    if (!state.selectedId) return null
    return state.convocatorias?.find((c) => c.id === state.selectedId) ?? null
  }, [state.convocatorias, state.selectedId])
}
