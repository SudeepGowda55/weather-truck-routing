import type { RiskKey } from './types'

export const RISK_LEVELS: RiskKey[] = ['low', 'moderate', 'high', 'severe', 'no_travel']

export const RISK_LABEL: Record<RiskKey, string> = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  severe: 'Severe',
  no_travel: 'No Travel',
}

export const RISK_COLOR: Record<RiskKey, string> = {
  low: '#2f9e44',
  moderate: '#e8b923',
  high: '#f07c13',
  severe: '#d6336c',
  no_travel: '#5c1a8a',
}

export const ROUTE_COLOR = ['#1c5fd6', '#0d9488', '#9b4dca']

export function duration(seconds: number) {
  const minutes = Math.round(seconds / 60)
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h ? `${h} h ${String(m).padStart(2, '0')} m` : `${m} min`
}

const timeFmt = new Intl.DateTimeFormat(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' })

export function clock(iso: string) {
  return timeFmt.format(new Date(iso))
}

export function miles(n: number) {
  return `${Math.round(n).toLocaleString()} mi`
}

export function toLocalInput(date: Date) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}
