from dataclasses import dataclass
from datetime import datetime, timedelta

from .geo import bearing, interpolate, offset, point_at, simplify
from .providers import openmeteo
from .risk import Risk, assess

HEATMAP_HOURS = 48
CORRIDOR_STEP_MI = 20
CORRIDOR_OFFSETS_MI = (-30, 0, 30)
HEAT_CELL_DEG = 0.4
MAX_HEAT_POINTS = 160
WEATHER_BUDGET = 330


@dataclass
class Checkpoint:
    mile: float
    point: tuple
    eta: datetime
    covers_mi: float


def make_checkpoints(route, departure, every_mi):
    total = route.miles[-1]
    marks = [n * every_mi for n in range(int(total // every_mi) + 1)]
    if total - marks[-1] > 0.5:
        marks.append(total)
    else:
        marks[-1] = total

    # each checkpoint stands for half the gap back and half the gap forward,
    # so the miles add up to the full route
    out = []
    for i, mile in enumerate(marks):
        back = (mile - marks[i - 1]) / 2 if i > 0 else 0
        ahead = (marks[i + 1] - mile) / 2 if i < len(marks) - 1 else 0
        eta = departure + timedelta(seconds=interpolate(route.miles, route.seconds, mile))
        out.append(Checkpoint(mile, point_at(route.points, route.miles, mile), eta, back + ahead))
    return out


def summarize(readings):
    miles = {r.key: 0.0 for r in Risk}
    weighted = total = 0.0
    for c in readings:
        level = Risk[c["risk"].upper()]
        miles[c["risk"]] += c["covers_mi"]
        weighted += level * c["covers_mi"]
        total += c["covers_mi"]
    worst = max((Risk[c["risk"].upper()] for c in readings), default=Risk.LOW)
    return {
        "miles_by_risk": {k: round(v, 1) for k, v in miles.items()},
        "average_risk": round(weighted / total, 3) if total else 0.0,
        "worst": worst.key,
    }


def rank_key(route):
    # brief: fewest severe miles, then high miles, then avg risk, then time.
    # no-travel miles go first so a route the rules forbid never wins
    m = route["summary"]["miles_by_risk"]
    return (m["no_travel"], m["severe"], m["high"], route["summary"]["average_risk"], route["duration_s"])


def format_duration(seconds):
    minutes = round(seconds / 60)
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60} h {minutes % 60:02d} min"


def explain(best, others):
    if not others:
        return "Only one route was found for this trip."
    labels = ["No Travel miles", "Severe miles", "High miles"]
    b = rank_key(best)
    parts = []
    for o in others:
        k = rank_key(o)
        i = next((n for n in range(5) if k[n] != b[n]), 4)
        if i < 3:
            parts.append(f"{o['name']} has {k[i]:.0f} {labels[i]} vs {b[i]:.0f}")
        elif i == 3:
            parts.append(f"{o['name']} has higher average risk ({k[3]:.2f} vs {b[3]:.2f})")
        else:
            parts.append(f"{o['name']} is {format_duration(k[4] - b[4])} slower with the same risk")
    return "; ".join(parts) + "."


def corridor_points(routes):
    seen, out = set(), []
    for r in routes:
        d = 0.0
        while d <= r.miles[-1]:
            here = point_at(r.points, r.miles, d)
            ahead = point_at(r.points, r.miles, min(d + 2, r.miles[-1]))
            side = bearing(here, ahead) + 90
            for lateral in CORRIDOR_OFFSETS_MI:
                p = offset(here, side, lateral) if lateral else here
                cell = (round(p[0] / HEAT_CELL_DEG), round(p[1] / HEAT_CELL_DEG))
                if cell not in seen:
                    seen.add(cell)
                    out.append(p)
            d += CORRIDOR_STEP_MI

    if len(out) > MAX_HEAT_POINTS:
        step = len(out) / MAX_HEAT_POINTS
        out = [out[int(i * step)] for i in range(MAX_HEAT_POINTS)]
    return out


def checkpoint_json(c, weather, a):
    return {
        "mile": round(c.mile, 1),
        "lat": round(c.point[0], 5),
        "lon": round(c.point[1], 5),
        "eta": c.eta.isoformat(),
        "covers_mi": round(c.covers_mi, 2),
        "risk": a.level.key,
        "wind_risk": a.wind.key,
        "rain_risk": a.rain.key,
        "snow_risk": a.snow.key,
        "reasons": a.reasons,
        **{k: round(v, 2) for k, v in weather.items()},
    }


def weather_cell(points, budget=WEATHER_BUDGET):
    # the free weather API counts each location as a call (600/min), so long trips at 10-mile
    # spacing get a coarser lookup grid instead of failing
    for cell in (0.1, 0.15, 0.2, 0.3, 0.4, 0.6):
        if len({openmeteo.snap(p, cell) for p in points}) <= budget:
            return cell
    return 0.8


def plan(routes, departure, load_lb, every_mi):
    stops = [make_checkpoints(r, departure, every_mi) for r in routes]
    grid = corridor_points(routes)
    longest_trip_h = max(r.duration_s for r in routes) / 3600
    hours = max(HEATMAP_HOURS, int(longest_trip_h) + 2)

    cp_points = [c.point for s in stops for c in s]
    series = iter(openmeteo.forecast(cp_points, departure, hours, cell=weather_cell(cp_points)))
    heat = openmeteo.forecast(grid, departure, hours, cell=HEAT_CELL_DEG) if grid else []

    result = []
    for i, (route, route_stops) in enumerate(zip(routes, stops)):
        readings = []
        for c in route_stops:
            weather = next(series).at(c.eta)
            a = assess(weather["wind_mph"], weather["rain_in_hr"], weather["snow_in_hr"], load_lb)
            readings.append(checkpoint_json(c, weather, a))
        result.append({
            "id": i,
            "name": f"Route {'ABC'[i]}",
            "via": route.via,
            "distance_mi": round(route.distance_mi, 1),
            "duration_s": round(route.duration_s),
            "arrival": (departure + timedelta(seconds=route.duration_s)).isoformat(),
            "geometry": [[round(lon, 5), round(lat, 5)] for lat, lon in simplify(route.points)],
            "checkpoints": readings,
            "summary": summarize(readings),
        })

    ranked = sorted(result, key=rank_key)
    best = ranked[0]
    for r in result:
        r["recommended"] = r is best
        r["rank"] = ranked.index(r) + 1

    start = heat[0].start if heat else departure
    times = [start + timedelta(hours=h) for h in range(HEATMAP_HOURS + 1)]
    risk, wind, precip = [], [], []
    for t in times:
        values = [s.at(t) for s in heat]
        risk.append([int(assess(v["wind_mph"], v["rain_in_hr"], v["snow_in_hr"], load_lb).level) for v in values])
        wind.append([round(v["wind_mph"]) for v in values])
        precip.append([round(v["rain_in_hr"] + v["snow_in_hr"], 2) for v in values])

    return {
        "departure": departure.isoformat(),
        "load_lb": load_lb,
        "interval_mi": every_mi,
        "routes": result,
        "recommended": best["id"],
        "reason": explain(best, [r for r in ranked if r is not best]),
        "heatmap": {
            "points": [[round(p[1], 4), round(p[0], 4)] for p in grid],
            "hours": [t.isoformat() for t in times],
            "risk": risk,
            "wind_mph": wind,
            "precip_in_hr": precip,
        },
    }
