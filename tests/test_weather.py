import pytest

import evie.tools  # noqa: F401
from evie.core import registry
from evie.services import weather


class Resp:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def fake_net(places=None, calls=None):
    """Fake Open-Meteo: `places` maps a lowercase name to its geocoding result."""
    places = places if places is not None else {"mumbai": {"name": "Mumbai", "country": "India", "latitude": 19.07, "longitude": 72.87}}

    def get(url, params=None, timeout=None):
        if calls is not None:
            calls.append((url, dict(params)))
        if "geocoding" in url:
            r = places.get(params["name"].lower())
            return Resp({"results": [r]} if r else {})
        return Resp({
            "current": {"temperature_2m": 29.4, "apparent_temperature": 33.2, "weather_code": 2, "wind_speed_10m": 11.6},
            "daily": {"temperature_2m_max": [32.1], "temperature_2m_min": [26.8], "precipitation_probability_max": [40]},
        })

    return get


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch):
    monkeypatch.setattr(weather, "_places", {})


def test_spoken_style_line():
    out = weather.weather("Mumbai", get=fake_net())
    assert out == ("Mumbai, India: 29 degrees, feels like 33, partly cloudy. "
                   "Today 27 to 32, 40 percent chance of rain. Wind 12 kilometres per hour.")


def test_unknown_place_is_said_not_guessed():
    with pytest.raises(weather.WeatherError, match="couldn't find a place called Atlantis"):
        weather.weather("Atlantis", get=fake_net())


def test_network_failure_is_spoken():
    def down(*a, **k):
        raise OSError("offline")

    with pytest.raises(weather.WeatherError, match="couldn't reach"):
        weather.weather("Mumbai", get=down)


def test_place_lookup_is_remembered_for_the_session():
    calls = []
    get = fake_net(calls=calls)
    weather.weather("Mumbai", get=get)
    weather.weather("mumbai", get=get)
    assert sum("geocoding" in u for u, _ in calls) == 1 and sum("forecast" in u for u, _ in calls) == 2


def test_tool_defaults_to_mumbai_and_accepts_a_location(monkeypatch):
    asked = []
    monkeypatch.setattr(weather, "weather", lambda loc: asked.append(loc) or f"weather for {loc}")
    assert registry.call("get_weather", {}) == "weather for Mumbai"
    assert registry.call("get_weather", {"location": "Pune"}) == "weather for Pune"
    assert asked == ["Mumbai", "Pune"]


def test_tool_turns_errors_into_sentences(monkeypatch):
    def boom(loc):
        raise weather.WeatherError("I couldn't find a place called X.")

    monkeypatch.setattr(weather, "weather", boom)
    assert registry.call("get_weather", {"location": "X"}) == "I couldn't find a place called X."
