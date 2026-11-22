from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests
from django.conf import settings
from django.core.cache import cache

VARIABLES = ("wind_speed_10m", "wind_gusts_10m", "rain", "snowfall", "temperature_2m")
BATCH = 80


class WeatherError(Exception):
    pass


@dataclass
class Series:
    start: datetime
    wind_mph: list
    gust_mph: list
    rain_in: list
    snow_in: list
    temp_f: list

    def at(self, when):
        # linear between the two hourly values around `when`
        h = (when - self.start).total_seconds() / 3600
        last = len(self.wind_mph) - 1
        i = max(0, min(int(h), last))
        j = min(i + 1, last)
        t = 0 if i == j else max(0.0, min(h - i, 1.0))

        def lerp(xs):
            return xs[i] + t * (xs[j] - xs[i])

        return {
            "wind_mph": lerp(self.wind_mph),
            "gust_mph": lerp(self.gust_mph),
            "rain_in_hr": lerp(self.rain_in),
            "snow_in_hr": lerp(self.snow_in),
            "temp_f": lerp(self.temp_f),
        }


def snap(p, cell):
    return (round(round(p[0] / cell) * cell, 3), round(round(p[1] / cell) * cell, 3))


def cache_key(p, start, hours):
    return f"om:{p[0]}:{p[1]}:{start:%Y%m%d%H}:{hours}"


def forecast(points, start, hours, cell=0.1):
    """Hourly forecast for each point from `start` (floored to the hour, UTC) for `hours` hours.

    Points are snapped to a `cell`-degree grid first: Open-Meteo counts every location as one call
    against its free per-minute limit, and the models aren't finer than ~0.1 degree anyway.
    """
    start = start.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=hours)
    unique = list(dict.fromkeys(snap(p, cell) for p in points))

    found, missing = {}, []
    for p in unique:
        hit = cache.get(cache_key(p, start, hours))
        if hit:
            found[p] = hit
        else:
            missing.append(p)

    for i in range(0, len(missing), BATCH):
        chunk = missing[i:i + BATCH]
        params = {
            "latitude": ",".join(str(p[0]) for p in chunk),
            "longitude": ",".join(str(p[1]) for p in chunk),
            "hourly": ",".join(VARIABLES),
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "temperature_unit": "fahrenheit",
            "timezone": "UTC",
            "start_hour": start.strftime("%Y-%m-%dT%H:%M"),
            "end_hour": end.strftime("%Y-%m-%dT%H:%M"),
        }
        try:
            res = requests.get(settings.OPEN_METEO_URL, params=params, headers=settings.HTTP_HEADERS, timeout=25)
        except requests.RequestException as exc:
            raise WeatherError(f"Weather service unreachable: {exc}") from exc
        if res.status_code == 429:
            raise WeatherError("The free weather service is busy (rate limit). Try again in a minute.")
        if res.status_code != 200:
            raise WeatherError(res.json().get("reason", f"Weather request failed ({res.status_code})"))

        body = res.json()
        if not isinstance(body, list):
            body = [body]
        for p, item in zip(chunk, body):
            hourly = item["hourly"]
            values = [[x or 0.0 for x in hourly[name]] for name in VARIABLES]
            found[p] = Series(start, *values)
            cache.set(cache_key(p, start, hours), found[p], 900)

    return [found[snap(p, cell)] for p in points]
