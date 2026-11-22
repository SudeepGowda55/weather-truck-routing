import { useRef, useState } from 'react'
import { planTrip } from './api'
import CheckpointTable from './components/CheckpointTable'
import MapView from './components/MapView'
import RouteList from './components/RouteList'
import TripForm from './components/TripForm'
import { RISK_COLOR, RISK_LABEL, RISK_LEVELS } from './format'
import type { Plan, TripRequest } from './types'

export default function App() {
  const [plan, setPlan] = useState<Plan | null>(null)
  const [selected, setSelected] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const inflight = useRef<AbortController | null>(null)

  async function run(trip: TripRequest) {
    inflight.current?.abort()
    const ctrl = new AbortController()
    inflight.current = ctrl
    setLoading(true)
    setError('')
    try {
      const result = await planTrip(trip, ctrl.signal)
      setPlan(result)
      setSelected(result.recommended)
    } catch (e) {
      if ((e as Error).name !== 'AbortError') setError((e as Error).message)
    } finally {
      if (inflight.current === ctrl) setLoading(false)
    }
  }

  const route = plan?.routes.find((r) => r.id === selected)

  return (
    <div className="app">
      <aside className="panel">
        <header className="brand">
          <h1>Weather-Aware Truck Routing</h1>
          <a className="gh" href="https://github.com/SudeepGowda55/weather-truck-routing" target="_blank" rel="noreferrer" aria-label="GitHub repository">
            <svg viewBox="0 0 16 16" width="18" height="18" fill="currentColor" aria-hidden="true">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8" />
            </svg>
          </a>
        </header>
        <TripForm loading={loading} onSubmit={run} />
        {error && <p className="form-error">{error}</p>}
        {plan && <RouteList plan={plan} selected={selected} onSelect={setSelected} />}
        {route && <CheckpointTable route={route} />}
        <footer className="legend">
          {RISK_LEVELS.map((k) => (
            <span key={k}>
              <i style={{ background: RISK_COLOR[k] }} />
              {RISK_LABEL[k]}
            </span>
          ))}
        </footer>
      </aside>
      <main className="stage">
        <MapView plan={plan} selected={selected} onSelect={setSelected} />
        {loading && <div className="loading">Routing three options and pulling forecasts…</div>}
      </main>
    </div>
  )
}
