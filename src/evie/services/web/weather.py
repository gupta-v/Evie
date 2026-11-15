"""Current weather and today's outlook from Open-Meteo (free, no key). One short spoken-style line.

Two calls: find the place by name, then its forecast. Place lookups are remembered for the session.
"""
from datetime import datetime, timedelta, timezone
from typing import Callable

_GEO = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT = 6

# WMO weather codes, grouped the way people say them
_CODES = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "foggy", 48: "foggy",
          51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "freezing drizzle", 57: "freezing drizzle",
          61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
          71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
          80: "light showers", 81: "showers", 82: "heavy showers", 85: "snow showers", 86: "heavy snow showers",
          95: "a thunderstorm", 96: "a thunderstorm with hail", 99: "a thunderstorm with hail"}

_places: dict[str, dict] = {}


class WeatherError(Exception):
    """Message is safe to read aloud."""


def _get(url: str, params: dict, get: Callable | None = None) -> dict:
    import httpx

    try:
        r = (get or httpx.get)(url, params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise WeatherError("I couldn't reach the weather service right now.") from e


def _place(name: str, get) -> dict:
    key = name.strip().lower()
    if key not in _places:
        found = _get(_GEO, {"name": name, "count": 1, "language": "en", "format": "json"}, get).get("results")
        if not found:
            raise WeatherError(f"I couldn't find a place called {name}.")
        _places[key] = found[0]
    return _places[key]


def _num(x) -> int:
    return round(x)


def _stamp(d: dict, now: datetime) -> str:
    """'9:20 PM there, updated 3 minutes ago' from Open-Meteo's local reading time; '' if it gave none."""
    try:
        local = datetime.fromisoformat(d["current"]["time"])
        age = now - (local - timedelta(seconds=d["utc_offset_seconds"])).replace(tzinfo=timezone.utc)
    except (KeyError, ValueError):
        return ""
    mins = max(0, int(age.total_seconds() // 60))
    when = "just now" if mins < 1 else f"{mins} minute{'s' * (mins != 1)} ago"
    return f" It is {local.strftime('%I:%M %p').lstrip('0')} there, updated {when}."


def weather(location: str, get: Callable | None = None, now: datetime | None = None) -> str:
    p = _place(location, get)
    d = _get(_FORECAST, {
        "latitude": p["latitude"], "longitude": p["longitude"], "timezone": "auto", "forecast_days": 1,
        "current": "is_day,temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
    }, get)
    c, day = d["current"], d["daily"]
    where = p["name"] + (f", {p['country']}" if p.get("country") else "")
    out = f"{where}: {_num(c['temperature_2m'])} degrees, feels like {_num(c['apparent_temperature'])}, {_CODES.get(c['weather_code'], 'unsettled')}."
    out += f" Today {_num(day['temperature_2m_min'][0])} to {_num(day['temperature_2m_max'][0])}"
    rain = (day.get("precipitation_probability_max") or [None])[0]
    out += f", {_num(rain)} percent chance of rain." if rain is not None else "."
    out += f" Wind {_num(c['wind_speed_10m'])} kilometres per hour."
    out += _stamp(d, now or datetime.now(timezone.utc))
    return out + ("" if c.get("is_day", 1) else " It is night there now, so today's high has already passed.")
