export const NOT_RECORDED = 'Not recorded'

export function metric(value: number | null | undefined, digits = 4) {
  return value === null || value === undefined ? NOT_RECORDED : value.toFixed(digits)
}

export function count(value: number | null | undefined) {
  return value === null || value === undefined ? NOT_RECORDED : value.toLocaleString()
}

export function milliseconds(value: number | null | undefined) {
  if (value === null || value === undefined) return NOT_RECORDED
  return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${Math.round(value)} ms`
}

export function dateTime(value: string | null | undefined) {
  if (!value) return NOT_RECORDED
  return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function bytes(value: number | null | undefined) {
  if (value === null || value === undefined) return NOT_RECORDED
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}
