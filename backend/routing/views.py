import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

import requests
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .planner import plan
from .providers import geocode
from .providers.openmeteo import WeatherError
from .providers.valhalla import RoutingError, find_routes

log = logging.getLogger(__name__)

INTERVALS = (10, 25, 50)
MAX_LOAD_LB = 120_000


def bad_request(message):
    return JsonResponse({"error": message}, status=400)


@require_GET
def health(request):
    return JsonResponse({"ok": True})


@require_GET
def places(request):
    try:
        return JsonResponse({"results": geocode.search(request.GET.get("q", ""))})
    except requests.RequestException:
        log.exception("geocoding failed")
        return JsonResponse({"error": "Place search is unavailable right now."}, status=502)


def parse_point(value):
    lat, lon = float(value["lat"]), float(value["lon"])
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError
    return (lat, lon)


@csrf_exempt
@require_POST
def plan_trip(request):
    try:
        body = json.loads(request.body)
        origin = parse_point(body["origin"])
        destination = parse_point(body["destination"])
        departure = datetime.fromisoformat(body["departure"].replace("Z", "+00:00"))
        load_lb = float(body["load_lb"])
        interval = int(body.get("interval_mi", 25))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return bad_request("Send origin, destination (lat/lon), departure (ISO time) and load_lb.")

    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if departure < now - timedelta(hours=1) or departure > now + timedelta(days=10):
        return bad_request("Departure must be between now and 10 days ahead (the forecast range).")
    if not 0 <= load_lb <= MAX_LOAD_LB:
        return bad_request(f"Load weight must be between 0 and {MAX_LOAD_LB:,} lb.")
    if interval not in INTERVALS:
        return bad_request("Checkpoint interval must be 10, 25 or 50 miles.")
    if origin == destination:
        return bad_request("Origin and destination are the same place.")

    key = "plan:" + hashlib.sha1(json.dumps([origin, destination, departure.isoformat(), load_lb, interval]).encode()).hexdigest()
    cached = cache.get(key)
    if cached:
        return JsonResponse(cached)

    try:
        routes = find_routes(origin, destination, load_lb)
        result = plan(routes, departure, load_lb, interval)
    except RoutingError as exc:
        return JsonResponse({"error": str(exc)}, status=502)
    except WeatherError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    cache.set(key, result, 600)
    return JsonResponse(result)
