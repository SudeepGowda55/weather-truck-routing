from dataclasses import dataclass, field
from enum import IntEnum


class Risk(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def key(self):
        return self.name.lower()


# lower edges of moderate / high / severe
WIND_MPH = (25, 35, 45)
RAIN_IN_HR = (0.10, 0.25, 0.50)
SNOW_IN_HR = (0.5, 1.0, 2.0)

WIND_NO_TRAVEL = 55
RAIN_NO_TRAVEL = 1.00
SNOW_NO_TRAVEL = 3.0

HEAVY_LOAD_LB = 30_000
VERY_HEAVY_LOAD_LB = 40_000


def band(value, edges):
    # values on a shared edge (e.g. 0.25 in/hr rain) go to the higher band
    if value >= edges[2]:
        return Risk.SEVERE
    if value >= edges[1]:
        return Risk.HIGH
    if value >= edges[0]:
        return Risk.MODERATE
    return Risk.LOW


def wind_risk(mph, load_lb):
    if mph >= WIND_NO_TRAVEL:
        return Risk.NO_TRAVEL
    level = band(mph, WIND_MPH)
    if level == Risk.SEVERE and load_lb > HEAVY_LOAD_LB:
        return Risk.NO_TRAVEL
    if level == Risk.HIGH and load_lb > VERY_HEAVY_LOAD_LB:
        return Risk.SEVERE
    return level


def rain_risk(in_hr):
    return Risk.NO_TRAVEL if in_hr > RAIN_NO_TRAVEL else band(in_hr, RAIN_IN_HR)


def snow_risk(in_hr):
    return Risk.NO_TRAVEL if in_hr > SNOW_NO_TRAVEL else band(in_hr, SNOW_IN_HR)


@dataclass(frozen=True)
class Assessment:
    level: Risk
    wind: Risk
    rain: Risk
    snow: Risk
    reasons: list = field(default_factory=list)


def assess(wind_mph, rain_in_hr, snow_in_hr, load_lb):
    wind = wind_risk(wind_mph, load_lb)
    rain = rain_risk(rain_in_hr)
    snow = snow_risk(snow_in_hr)
    level = max(wind, rain, snow)

    reasons = []
    if level > Risk.LOW:
        if wind == level:
            load_note = ""
            if wind != band(wind_mph, WIND_MPH) and wind_mph < WIND_NO_TRAVEL:
                load_note = f" with {load_lb:,.0f} lb load"
            reasons.append(f"wind {wind_mph:.0f} mph{load_note}")
        if rain == level:
            reasons.append(f"rain {rain_in_hr:.2f} in/hr")
        if snow == level:
            reasons.append(f"snow {snow_in_hr:.1f} in/hr")
    return Assessment(level, wind, rain, snow, reasons)
