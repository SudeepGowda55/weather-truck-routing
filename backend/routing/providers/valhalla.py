from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import requests
from django.conf import settings

from ..geo import bearing, cumulative_miles, decode_polyline, haversine_mi, offset, overlap_share

LB_PER_TONNE = 2204.62
EMPTY_TRUCK_LB = 35_000  # tractor + 53ft trailer, the form only asks for cargo weight

# the public server rejects requests whose locations are more than 1500 km apart in a straight line,
# so long trips are routed in hops and stitched together
MAX_HOP_MI = 600


class RoutingError(Exception):
    pass


@dataclass
class Route:
    points: list
    miles: list
    seconds: list
    distance_mi: float
    duration_s: float
    via: str


def request_trips(locations, load_lb, alternates=0):
    tonnes = min((EMPTY_TRUCK_LB + load_lb) / LB_PER_TONNE, 60)
    body = {
        "locations": locations,
        "costing": "truck",
        "costing_options": {"truck": {"weight": round(tonnes, 1)}},
        "units": "miles",
        "alternates": alternates,
    }
    try:
        res = requests.post(settings.VALHALLA_URL, json=body, headers=settings.HTTP_HEADERS, timeout=25)
    except requests.RequestException as exc:
        raise RoutingError(f"Routing service unreachable: {exc}") from exc

    data = res.json() if "json" in res.headers.get("content-type", "") else {}
    if res.status_code != 200 or "trip" not in data:
        raise RoutingError(data.get("error") or f"Routing failed ({res.status_code})")
    return [data["trip"]] + [a["trip"] for a in data.get("alternates", [])]


def stitch(trips, via):
    points, seconds, joins = [], [], []
    elapsed = 0.0
    for trip in trips:
        for leg in trip["legs"]:
            shape = decode_polyline(leg["shape"])
            miles = cumulative_miles(shape)
            leg_seconds = [0.0] * len(shape)
            # spread each maneuver's time over its part of the shape
            for m in leg["maneuvers"]:
                a, b = m["begin_shape_index"], m["end_shape_index"]
                span = miles[b] - miles[a]
                for i in range(a + 1, b + 1):
                    share = (miles[i] - miles[a]) / span if span else 1
                    leg_seconds[i] = leg_seconds[a] + share * m["time"]
            skip = 1 if points else 0
            points.extend(shape[skip:])
            seconds.extend(elapsed + s for s in leg_seconds[skip:])
            elapsed = seconds[-1]

        joins.append(len(points) - 1)

    for j in reversed(joins[:-1]):
        points, seconds = trim_spur(points, seconds, j)

    miles = cumulative_miles(points)
    return Route(points, miles, seconds, miles[-1], seconds[-1], via)


def trim_spur(points, seconds, j, tolerance_mi=0.06, reach_mi=15):
    # a hop that ends off the main road drives in and back out again; cut the out-and-back
    miles = cumulative_miles(points)
    lo = j
    while lo > 0 and miles[j] - miles[lo - 1] <= reach_mi:
        lo -= 1
    hi = j
    while hi < len(points) - 1 and miles[hi + 1] - miles[j] <= reach_mi:
        hi += 1
    cut = None
    for a in range(lo, j):
        for b in range(hi, j, -1):
            if haversine_mi(points[a], points[b]) < tolerance_mi:
                cut = (a, b)
                break
        if cut:
            break
    if not cut:
        return points, seconds
    a, b = cut
    saved = seconds[b] - seconds[a]
    return points[:a + 1] + points[b + 1:], seconds[:a + 1] + [t - saved for t in seconds[b + 1:]]


def compass(deg):
    return ["northern", "eastern", "southern", "western"][int(((deg % 360) + 45) // 90) % 4]


def location(p, major_roads=False):
    loc = {"lat": p[0], "lon": p[1]}
    if major_roads:
        # don't let a detour point pull the truck down a farm road
        loc.update(radius=30000, search_filter={"min_road_class": "primary"})
    return loc


def chain(origin, destination, push_mi=0.0):
    """Waypoints from origin to destination at most MAX_HOP_MI apart, pushed sideways by push_mi."""
    crow = haversine_mi(origin, destination)
    hops = max(1, int(crow // MAX_HOP_MI) + 1)
    if push_mi and hops == 1:
        hops = 2
    heading = bearing(origin, destination)
    points = [origin]
    for k in range(1, hops):
        on_line = offset(origin, heading, crow * k / hops)
        points.append(offset(on_line, heading + 90, push_mi) if push_mi else on_line)
    return points + [destination]


def route_chain(points, load_lb, via):
    hops = list(zip(points, points[1:]))
    with ThreadPoolExecutor(max_workers=3) as pool:
        trips = list(pool.map(lambda h: request_trips([location(h[0], h[0] != points[0]), location(h[1], h[1] != points[-1])], load_lb)[0], hops))
    return stitch(trips, via)


def find_routes(origin, destination, load_lb, wanted=3):
    crow = haversine_mi(origin, destination)
    if crow < 925:  # just under the server's 1500 km limit
        locations = [location(origin), location(destination)]
        trips = request_trips(locations, load_lb, wanted - 1)
        routes = [stitch([t], "fastest" if i == 0 else "alternate") for i, t in enumerate(trips)]
    else:
        routes = [route_chain(chain(origin, destination), load_lb, "fastest")]

    # fill the remaining options by pushing the path to either side of the corridor
    main = routes[0]
    heading = bearing(origin, destination)
    base_push = min(max(crow * 0.12, 12), 120)
    for scale in (1, 1.8):
        for side in (-1, 1):
            if len(routes) >= wanted:
                return routes
            name = f"{compass(heading + 90 * side)} detour"
            try:
                candidate = route_chain(chain(origin, destination, side * base_push * scale), load_lb, name)
            except RoutingError:
                continue
            new_road = all(overlap_share(candidate.points, r.points) < 0.85 for r in routes)
            if new_road and candidate.duration_s < main.duration_s * 1.6:
                routes.append(candidate)
    return routes
