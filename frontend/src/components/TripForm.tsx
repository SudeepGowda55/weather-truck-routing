import { useState } from 'react'
import { toLocalInput } from '../format'
import type { Place, TripRequest } from '../types'
import PlaceInput from './PlaceInput'

interface Props {
  loading: boolean
  onSubmit: (trip: TripRequest) => void
}

const INTERVALS = [10, 25, 50]

function nextHour() {
  const d = new Date()
  d.setHours(d.getHours() + 1, 0, 0, 0)
  return d
}

export default function TripForm({ loading, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place | null>({ label: 'Chicago, Illinois, United States', lat: 41.8781, lon: -87.6298 })
  const [destination, setDestination] = useState<Place | null>({ label: 'Denver, Colorado, United States', lat: 39.7392, lon: -104.9903 })
  const [departure, setDeparture] = useState(toLocalInput(nextHour()))
  const [load, setLoad] = useState('42000')
  const [interval, setInterval] = useState(25)
  const [error, setError] = useState('')

  const now = new Date()
  const max = new Date(now.getTime() + 10 * 24 * 3600 * 1000)

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const loadLb = Number(load)
    if (!origin || !destination) return setError('Pick the origin and destination from the suggestions.')
    if (!Number.isFinite(loadLb) || loadLb < 0 || loadLb > 120000) return setError('Load weight must be between 0 and 120,000 lb.')
    const when = new Date(departure)
    if (Number.isNaN(when.getTime())) return setError('Enter a departure date and time.')
    setError('')
    onSubmit({ origin, destination, departure: when.toISOString(), load_lb: loadLb, interval_mi: interval })
  }

  function swap() {
    setOrigin(destination)
    setDestination(origin)
  }

  return (
    <form className="trip-form" onSubmit={submit}>
      <div className="od">
        <PlaceInput label="From" value={origin} onChange={setOrigin} placeholder="City or address" />
        <button type="button" className="swap" onClick={swap} aria-label="Swap origin and destination">
          ⇅
        </button>
        <PlaceInput label="To" value={destination} onChange={setDestination} placeholder="City or address" />
      </div>
      <div className="row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input
            id="departure"
            type="datetime-local"
            value={departure}
            min={toLocalInput(now)}
            max={toLocalInput(max)}
            onChange={(e) => setDeparture(e.target.value)}
          />
        </div>
        <div className="field load">
          <label htmlFor="load">Load (lb)</label>
          <input id="load" type="number" inputMode="numeric" min={0} max={120000} step={500} value={load} onChange={(e) => setLoad(e.target.value)} />
        </div>
      </div>
      <div className="field">
        <span className="label">Weather every</span>
        <div className="segmented" role="radiogroup" aria-label="Checkpoint spacing">
          {INTERVALS.map((n) => (
            <button key={n} type="button" role="radio" aria-checked={interval === n} className={interval === n ? 'on' : ''} onClick={() => setInterval(n)}>
              {n} mi
            </button>
          ))}
        </div>
      </div>
      {error && <p className="form-error">{error}</p>}
      <button className="primary" disabled={loading}>
        {loading ? 'Checking routes and weather…' : 'Find the safest route'}
      </button>
    </form>
  )
}
