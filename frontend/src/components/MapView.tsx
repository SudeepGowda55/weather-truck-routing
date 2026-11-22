import maplibregl, { type GeoJSONSource, type Map as MLMap } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import { RISK_COLOR, RISK_LABEL, ROUTE_COLOR, clock } from '../format'
import { bounds, cumulative, slice } from '../geo'
import type { Plan, RouteOption } from '../types'
import type { Metric } from './HeatmapControls'

const STYLE = 'https://tiles.openfreemap.org/styles/positron'
const EMPTY = { type: 'FeatureCollection' as const, features: [] }

interface Props {
  plan: Plan | null
  selected: number
  onSelect: (id: number) => void
  hour: number
  metric: Metric
}

// colour of each heat point for the hour on the slider. Each point keeps every hour as a property,
// so moving the slider only swaps this expression and nothing is re-uploaded.
// Points are coloured by their own value (not summed like a density heatmap), so calm stays green.
function heatColor(metric: Metric, hour: number) {
  if (metric === 'wind') {
    return ['interpolate', ['linear'], ['get', `w${hour}`], 0, '#d9f0e3', 12, '#7cc7a0', 24, '#2f9e44', 25, '#e8b923', 35, '#f07c13', 45, '#d6336c', 55, '#5c1a8a']
  }
  if (metric === 'precip') {
    return ['interpolate', ['linear'], ['get', `p${hour}`], 0, '#e8eef3', 0.01, '#bfe3f0', 0.1, '#38a3c9', 0.25, '#1c5fd6', 0.5, '#3730a3', 1, '#5c1a8a']
  }
  return ['match', ['get', `r${hour}`], 0, '#2f9e44', 1, '#e8b923', 2, '#f07c13', 3, '#d6336c', '#5c1a8a']
}

function heatOpacity(metric: Metric, hour: number) {
  // dry cells fade out in the precipitation view so the rain stands out
  if (metric === 'precip') return ['interpolate', ['linear'], ['get', `p${hour}`], 0, 0.12, 0.02, 0.5, 0.2, 0.7]
  return 0.38
}

// where the truck is on the route at a given time, from the checkpoint ETAs
function truckAt(route: RouteOption, when: number): [number, number] | null {
  const cps = route.checkpoints
  if (!cps.length) return null
  const times = cps.map((c) => Date.parse(c.eta))
  if (when <= times[0]) return [cps[0].lon, cps[0].lat]
  if (when >= times[times.length - 1]) return null
  const i = times.findIndex((t) => t > when)
  const a = cps[i - 1]
  const b = cps[i]
  const t = (when - times[i - 1]) / (times[i] - times[i - 1])
  return [a.lon + (b.lon - a.lon) * t, a.lat + (b.lat - a.lat) * t]
}

export default function MapView({ plan, selected, onSelect, hour, metric }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<MLMap | null>(null)
  const [ready, setReady] = useState(false)
  const selectRef = useRef(onSelect)
  selectRef.current = onSelect

  useEffect(() => {
    const m = new maplibregl.Map({
      container: container.current!,
      style: STYLE,
      center: [-96, 38.5],
      zoom: 3.6,
      attributionControl: { compact: true },
    })
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.current = m

    m.on('load', () => {
      m.addSource('heat', { type: 'geojson', data: EMPTY })
      m.addSource('truck', { type: 'geojson', data: EMPTY })
      m.addSource('routes', { type: 'geojson', data: EMPTY })
      m.addSource('segments', { type: 'geojson', data: EMPTY })
      m.addSource('checkpoints', { type: 'geojson', data: EMPTY })

      m.addLayer({
        id: 'heat',
        type: 'circle',
        source: 'heat',
        paint: {
          'circle-color': heatColor('risk', 0) as never,
          'circle-opacity': heatOpacity('risk', 0) as never,
          'circle-blur': 1,
          'circle-radius': ['interpolate', ['exponential', 2], ['zoom'], 3, 10, 6, 80, 9, 640],
        },
      })

      m.addLayer({
        id: 'routes-casing',
        type: 'line',
        source: 'routes',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: { 'line-color': '#ffffff', 'line-width': ['case', ['get', 'selected'], 11, 7] },
      })
      m.addLayer({
        id: 'routes',
        type: 'line',
        source: 'routes',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color': ['get', 'color'],
          'line-width': ['case', ['get', 'selected'], 7, 4],
          'line-opacity': ['case', ['get', 'selected'], 0.35, 0.75],
        },
      })
      m.addLayer({
        id: 'segments',
        type: 'line',
        source: 'segments',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: { 'line-color': ['get', 'color'], 'line-width': 5 },
      })
      m.addLayer({
        id: 'checkpoints',
        type: 'circle',
        source: 'checkpoints',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 3.5, 9, 7],
          'circle-color': ['get', 'color'],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 1.5,
        },
      })

      m.addLayer({
        id: 'truck',
        type: 'circle',
        source: 'truck',
        paint: { 'circle-radius': 8, 'circle-color': '#182430', 'circle-stroke-color': '#f2b705', 'circle-stroke-width': 3 },
      })

      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10, className: 'cp-popup' })
      m.on('mouseenter', 'checkpoints', (e) => {
        m.getCanvas().style.cursor = 'pointer'
        const f = e.features?.[0]
        if (!f) return
        const p = f.properties as Record<string, string>
        popup
          .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setHTML(
            `<strong>Mile ${p.mile}</strong> · ${p.eta}<br>` +
              `<span class="pill" style="background:${p.color}">${p.label}</span> ${p.reasons}<br>` +
              `Wind ${p.wind} mph (gusts ${p.gust}) · Rain ${p.rain} in/hr · Snow ${p.snow} in/hr · ${p.temp}°F`,
          )
          .addTo(m)
      })
      m.on('mouseleave', 'checkpoints', () => {
        m.getCanvas().style.cursor = ''
        popup.remove()
      })
      m.on('click', 'routes', (e) => {
        const id = e.features?.[0]?.properties?.id
        if (id !== undefined) selectRef.current(Number(id))
      })
      m.on('mouseenter', 'routes', () => (m.getCanvas().style.cursor = 'pointer'))
      m.on('mouseleave', 'routes', () => (m.getCanvas().style.cursor = ''))

      setReady(true)
    })
    return () => m.remove()
  }, [])

  // fit the map when a new plan comes in
  useEffect(() => {
    const m = map.current
    if (!m || !ready || !plan) return
    const all = plan.routes.flatMap((r) => r.geometry)
    m.fitBounds(bounds(all), { padding: { top: 60, bottom: 140, left: 60, right: 60 }, duration: 900 })
  }, [plan, ready])

  useEffect(() => {
    const m = map.current
    if (!m || !ready) return
    const routes = plan?.routes ?? []
    const route = routes.find((r) => r.id === selected)

    ;(m.getSource('routes') as GeoJSONSource).setData({
      type: 'FeatureCollection',
      // selected route drawn last so it sits on top
      features: [...routes]
        .sort((a, b) => Number(a.id === selected) - Number(b.id === selected))
        .map((r) => ({
          type: 'Feature',
          properties: { id: r.id, selected: r.id === selected, color: ROUTE_COLOR[r.id % ROUTE_COLOR.length] },
          geometry: { type: 'LineString', coordinates: r.geometry },
        })),
    })

    const segments: GeoJSON.Feature[] = []
    const points: GeoJSON.Feature[] = []
    if (route) {
      const dist = cumulative(route.geometry)
      const scale = dist[dist.length - 1] / (route.checkpoints[route.checkpoints.length - 1]?.mile || 1)
      route.checkpoints.forEach((c, i, all) => {
        const from = i ? (all[i - 1].mile + c.mile) / 2 : 0
        const to = i < all.length - 1 ? (c.mile + all[i + 1].mile) / 2 : c.mile
        const coords = slice(route.geometry, dist, from * scale, to * scale)
        if (coords.length > 1) {
          segments.push({ type: 'Feature', properties: { color: RISK_COLOR[c.risk] }, geometry: { type: 'LineString', coordinates: coords } })
        }
        points.push({
          type: 'Feature',
          properties: {
            mile: Math.round(c.mile),
            eta: clock(c.eta),
            color: RISK_COLOR[c.risk],
            label: RISK_LABEL[c.risk],
            reasons: c.reasons.join(', '),
            wind: Math.round(c.wind_mph),
            gust: Math.round(c.gust_mph),
            rain: c.rain_in_hr.toFixed(2),
            snow: c.snow_in_hr.toFixed(1),
            temp: Math.round(c.temp_f),
          },
          geometry: { type: 'Point', coordinates: [c.lon, c.lat] },
        })
      })
    }
    ;(m.getSource('segments') as GeoJSONSource).setData({ type: 'FeatureCollection', features: segments })
    ;(m.getSource('checkpoints') as GeoJSONSource).setData({ type: 'FeatureCollection', features: points })
  }, [plan, selected, ready])

  useEffect(() => {
    const m = map.current
    if (!m || !ready) return
    const heat = plan?.heatmap
    ;(m.getSource('heat') as GeoJSONSource).setData({
      type: 'FeatureCollection',
      features: (heat?.points ?? []).map((pt, i) => {
        const props: Record<string, number> = {}
        heat!.hours.forEach((_, h) => {
          props[`r${h}`] = heat!.risk[h][i]
          props[`w${h}`] = heat!.wind_mph[h][i]
          props[`p${h}`] = heat!.precip_in_hr[h][i]
        })
        return { type: 'Feature', properties: props, geometry: { type: 'Point', coordinates: pt } }
      }),
    })
  }, [plan, ready])

  useEffect(() => {
    const m = map.current
    if (!m || !ready) return
    m.setPaintProperty('heat', 'circle-color', heatColor(metric, hour))
    m.setPaintProperty('heat', 'circle-opacity', heatOpacity(metric, hour))
  }, [hour, metric, ready])

  useEffect(() => {
    const m = map.current
    if (!m || !ready) return
    const route = plan?.routes.find((r) => r.id === selected)
    const at = route && plan ? truckAt(route, Date.parse(plan.heatmap.hours[hour])) : null
    ;(m.getSource('truck') as GeoJSONSource).setData({
      type: 'FeatureCollection',
      features: at ? [{ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: at } }] : [],
    })
  }, [plan, selected, hour, ready])

  return <div ref={container} className="map" aria-label="Map of route options and weather checkpoints" />
}
