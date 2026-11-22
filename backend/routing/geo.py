import math
from bisect import bisect_right

EARTH_RADIUS_MI = 3958.8


def haversine_mi(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def cumulative_miles(points):
    out = [0.0]
    for a, b in zip(points, points[1:]):
        out.append(out[-1] + haversine_mi(a, b))
    return out


def interpolate(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    i = bisect_right(xs, x) - 1
    span = xs[i + 1] - xs[i]
    t = 0 if span == 0 else (x - xs[i]) / span
    return ys[i] + t * (ys[i + 1] - ys[i])


def point_at(points, miles, target):
    lat = interpolate(miles, [p[0] for p in points], target)
    lon = interpolate(miles, [p[1] for p in points], target)
    return (lat, lon)


def offset(point, bearing_deg, distance_mi):
    lat, lon, b = math.radians(point[0]), math.radians(point[1]), math.radians(bearing_deg)
    d = distance_mi / EARTH_RADIUS_MI
    lat2 = math.asin(math.sin(lat) * math.cos(d) + math.cos(lat) * math.sin(d) * math.cos(b))
    lon2 = lon + math.atan2(math.sin(b) * math.sin(d) * math.cos(lat), math.cos(d) - math.sin(lat) * math.sin(lat2))
    return (math.degrees(lat2), (math.degrees(lon2) + 540) % 360 - 180)


def bearing(a, b):
    lat1, lat2, dlon = math.radians(a[0]), math.radians(b[0]), math.radians(b[1] - a[1])
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def decode_polyline(encoded, precision=6):
    points, index, lat, lon = [], 0, 0, 0
    factor = 10 ** precision
    while index < len(encoded):
        for axis in (0, 1):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if axis == 0:
                lat += delta
            else:
                lon += delta
        points.append((lat / factor, lon / factor))
    return points


def steps(start, stop, step):
    out, x = [], start
    while x < stop:
        out.append(x)
        x += step
    return out


def overlap_share(candidate, existing, tolerance_mi=1.0, step_mi=5.0):
    """How much of `candidate` runs within `tolerance_mi` of `existing` (0..1)."""
    cell = tolerance_mi / 69.0
    grid = {}
    # shape points can be miles apart on straight interstates, so densify first
    existing_miles = cumulative_miles(existing)
    dense = [point_at(existing, existing_miles, d) for d in steps(0, existing_miles[-1], tolerance_mi / 2)]
    for p in dense + [existing[-1]]:
        grid.setdefault((int(p[0] / cell), int(p[1] / cell)), []).append(p)

    miles = cumulative_miles(candidate)
    samples = [point_at(candidate, miles, d) for d in steps(0, miles[-1], step_mi)]
    if not samples:
        return 1.0

    near = 0
    for s in samples:
        gx, gy = int(s[0] / cell), int(s[1] / cell)
        close = [q for dx in range(-2, 3) for dy in range(-2, 3) for q in grid.get((gx + dx, gy + dy), [])]
        if any(haversine_mi(s, q) <= tolerance_mi for q in close):
            near += 1
    return near / len(samples)


def simplify(points, tolerance=0.0004):
    """Douglas-Peucker on lat/lon. 0.0004 deg is ~40 m, invisible at the zooms a whole route is seen at."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        (ay, ax), (by, bx) = points[first], points[last]
        dx, dy = bx - ax, by - ay
        norm = (dx * dx + dy * dy) ** 0.5 or 1e-12
        worst, index = 0.0, None
        for i in range(first + 1, last):
            py, px = points[i]
            dist = abs(dy * (px - ax) - dx * (py - ay)) / norm
            if dist > worst:
                worst, index = dist, i
        if index is not None and worst > tolerance:
            keep[index] = True
            stack += [(first, index), (index, last)]
    return [p for p, k in zip(points, keep) if k]
