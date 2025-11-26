from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

from .exceptions import ToolError

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass
class WeatherResult:
    temperature_c: float
    precip_prob_pct: int
    observed_at: str

    def to_dict(self) -> dict:
        return {
            "temperature_c": self.temperature_c,
            "precip_prob_pct": self.precip_prob_pct,
            "observed_at": self.observed_at,
        }


def get_weather(lat: float, lon: float, *, timeout: float = 10.0) -> WeatherResult:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,precipitation_probability",
        "hourly": "precipitation_probability",
        "timezone": "UTC",
    }
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise ToolError(f"Weather request failed: {exc}") from exc
    except ValueError as exc:
        raise ToolError("Weather response was not valid JSON") from exc

    current = payload.get("current")
    if not current:
        raise ToolError("Weather data unavailable: missing current block")

    temperature = current.get("temperature_2m")
    observed_at = current.get("time")
    if temperature is None or observed_at is None:
        raise ToolError("Weather data incomplete")

    precip_prob = current.get("precipitation_probability")
    if precip_prob is None:
        hourly = payload.get("hourly", {})
        hourly_prob = hourly.get("precipitation_probability") or []
        precip_prob = hourly_prob[0] if hourly_prob else 0

    return WeatherResult(
        temperature_c=float(temperature),
        precip_prob_pct=int(precip_prob),
        observed_at=observed_at,
    )


