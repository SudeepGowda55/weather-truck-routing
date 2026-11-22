import type { Place, Plan, TripRequest } from './types'

async function readError(res: Response) {
  try {
    const body = await res.json()
    return body.error ?? `Request failed (${res.status})`
  } catch {
    return `Request failed (${res.status})`
  }
}

export async function searchPlaces(q: string, signal?: AbortSignal): Promise<Place[]> {
  const res = await fetch(`/api/places?q=${encodeURIComponent(q)}`, { signal })
  if (!res.ok) throw new Error(await readError(res))
  return (await res.json()).results
}

export async function planTrip(trip: TripRequest, signal?: AbortSignal): Promise<Plan> {
  const res = await fetch('/api/plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      origin: { lat: trip.origin.lat, lon: trip.origin.lon },
      destination: { lat: trip.destination.lat, lon: trip.destination.lon },
      departure: trip.departure,
      load_lb: trip.load_lb,
      interval_mi: trip.interval_mi,
    }),
    signal,
  })
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}
