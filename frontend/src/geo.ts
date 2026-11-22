const R = 3958.8

export function haversine(a: [number, number], b: [number, number]) {
  const toRad = Math.PI / 180
  const dLat = (b[1] - a[1]) * toRad
  const dLon = (b[0] - a[0]) * toRad
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[1] * toRad) * Math.cos(b[1] * toRad) * Math.sin(dLon / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(h))
}

export function cumulative(coords: [number, number][]) {
  const out = [0]
  for (let i = 1; i < coords.length; i++) out.push(out[i - 1] + haversine(coords[i - 1], coords[i]))
  return out
}

function lerp(a: [number, number], b: [number, number], t: number): [number, number] {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
}

// part of a line between two distances along it, in miles
export function slice(coords: [number, number][], dist: number[], from: number, to: number) {
  const out: [number, number][] = []
  for (let i = 1; i < coords.length; i++) {
    const a = dist[i - 1]
    const b = dist[i]
    if (b < from) continue
    if (a > to) break
    const span = b - a || 1
    if (!out.length) out.push(lerp(coords[i - 1], coords[i], Math.max(0, (from - a) / span)))
    if (b <= to) out.push(coords[i])
    else {
      out.push(lerp(coords[i - 1], coords[i], (to - a) / span))
      break
    }
  }
  return out
}

export function bounds(coords: [number, number][]): [[number, number], [number, number]] {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (const [x, y] of coords) {
    if (x < minX) minX = x
    if (y < minY) minY = y
    if (x > maxX) maxX = x
    if (y > maxY) maxY = y
  }
  return [[minX, minY], [maxX, maxY]]
}
