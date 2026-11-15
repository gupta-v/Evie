import datetime
from typing import Annotated

from pydantic import Field

from evie.utils import config
from evie.core.registry import tool
from evie.services.web import weather


@tool
def get_time() -> str:
    """Get the current local date and time."""
    return datetime.datetime.now().strftime("%A %d %B %Y, %H:%M")


@tool
def get_weather(location: Annotated[str, Field(min_length=1)] = config.DEFAULT_LOCATION) -> str:
    """Get the current weather and today's outlook for a place. Use this for any question about
    weather, temperature, rain or whether to carry an umbrella. If the user does not name a place,
    leave location out and it uses their home city (Mumbai).

    Args:
        location: A city name such as Pune or London. Defaults to Mumbai.
    """
    try:
        return weather.weather(location)
    except weather.WeatherError as e:
        return str(e)
