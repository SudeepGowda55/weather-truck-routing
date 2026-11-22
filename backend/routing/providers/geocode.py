import requests
from django.conf import settings
from django.core.cache import cache


def search(query, limit=6):
    query = query.strip()
    if len(query) < 2:
        return []

    key = "geo:" + "_".join(query.lower().split()) + f":{limit}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    res = requests.get(settings.PHOTON_URL, params={"q": query, "limit": limit, "lang": "en"}, timeout=10)
    res.raise_for_status()

    places = {}
    for f in res.json().get("features", []):
        p = f["properties"]
        city = p.get("city") if p.get("city") != p.get("name") else None
        parts = [p.get("name"), city, p.get("state"), p.get("country")]
        label = ", ".join(dict.fromkeys(x for x in parts if x))
        lon, lat = f["geometry"]["coordinates"]
        places.setdefault(label, {"label": label, "lat": lat, "lon": lon})

    result = list(places.values())
    cache.set(key, result, 3600)
    return result
