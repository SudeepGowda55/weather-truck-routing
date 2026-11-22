export type RiskKey = 'low' | 'moderate' | 'high' | 'severe' | 'no_travel'

export interface Place {
  label: string
  lat: number
  lon: number
}

export interface Checkpoint {
  mile: number
  lat: number
  lon: number
  eta: string
  covers_mi: number
  risk: RiskKey
  wind_risk: RiskKey
  rain_risk: RiskKey
  snow_risk: RiskKey
  reasons: string[]
  wind_mph: number
  gust_mph: number
  rain_in_hr: number
  snow_in_hr: number
  temp_f: number
}

export interface RouteOption {
  id: number
  name: string
  via: string
  distance_mi: number
  duration_s: number
  arrival: string
  geometry: [number, number][]
  checkpoints: Checkpoint[]
  summary: {
    miles_by_risk: Record<RiskKey, number>
    average_risk: number
    worst: RiskKey
  }
  recommended: boolean
  rank: number
}

export interface Heatmap {
  points: [number, number][]
  hours: string[]
  risk: number[][]
  wind_mph: number[][]
  precip_in_hr: number[][]
}

export interface Plan {
  departure: string
  load_lb: number
  interval_mi: number
  routes: RouteOption[]
  recommended: number
  reason: string
  heatmap: Heatmap
}

export interface TripRequest {
  origin: Place
  destination: Place
  departure: string
  load_lb: number
  interval_mi: number
}
