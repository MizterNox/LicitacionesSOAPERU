// Utilidades de formato y fechas.
const _now = new Date()
export const TODAY = new Date(_now.getFullYear(), _now.getMonth(), _now.getDate())

export function fmtPEN(v) {
  if (v == null) return null
  return 'S/ ' + Math.round(v).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

export function parseISO(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function fmtDate(iso) {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

export function fmtDateShort(iso) {
  const [, m, d] = iso.split('-')
  return `${d}/${m}`
}

export function daysUntil(iso) {
  return Math.round((parseISO(iso) - TODAY) / 86400000)
}
