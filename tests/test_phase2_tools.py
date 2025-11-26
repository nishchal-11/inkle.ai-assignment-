from types import SimpleNamespace
from unittest.mock import patch

import pytest
import requests

from src.tools import GeocodeResult, PlaceResult, ToolError, WeatherResult
from src.tools import geocode_city, get_places, get_weather


@pytest.fixture(autouse=True)
def clear_geocode_cache():
    geocode_city.cache_clear()
    yield


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception("HTTP error")

    def json(self):
        return self._json


def test_geocode_success():
    mock_payload = [
        {
            "display_name": "Bengaluru, India",
            "lat": "12.9716",
            "lon": "77.5946",
            "address": {"country": "India"},
        }
    ]
    with patch("src.tools.geocode.requests.get", return_value=FakeResponse(mock_payload)):
        result = geocode_city("Bangalore")
        assert isinstance(result, GeocodeResult)
        assert result.name == "Bengaluru, India"
        assert result.lat == pytest.approx(12.9716)
        assert result.lon == pytest.approx(77.5946)
        assert result.country == "India"


def test_geocode_empty_returns_none():
    with patch("src.tools.geocode.requests.get", return_value=FakeResponse([])):
        assert geocode_city("Atlantis") is None


def test_geocode_failure_raises_toolerror():
    with patch(
        "src.tools.geocode.requests.get",
        side_effect=requests.RequestException("network down"),
    ):
        with pytest.raises(ToolError):
            geocode_city("Bangalore")


def test_geocode_fallback_on_403(monkeypatch):
    # Photon API returns GeoJSON format
    photon_payload = {
        "features": [
            {
                "geometry": {
                    "coordinates": [76.6413, 10.1632],  # [lon, lat]
                },
                "properties": {
                    "name": "Kerala, India",
                    "country": "India",
                },
            }
        ]
    }

    def mock_get(url, *args, **kwargs):
        if "nominatim" in url:
            response = SimpleNamespace()
            response.raise_for_status = lambda: (_ for _ in ()).throw(
                requests.HTTPError(response=SimpleNamespace(status_code=403))
            )
            response.json = lambda: []
            return response
        # Photon API response
        return FakeResponse(photon_payload)

    with patch("src.tools.geocode.requests.get", side_effect=mock_get):
        result = geocode_city("Kerala")
        assert result is not None
        assert result.name == "Kerala, India"


def test_weather_parsing_uses_current_block():
    mock_payload = {
        "current": {
            "temperature_2m": 25.5,
            "precipitation_probability": 40,
            "time": "2025-11-25T10:00:00Z",
        }
    }
    with patch("src.tools.weather.requests.get", return_value=FakeResponse(mock_payload)):
        result = get_weather(12.97, 77.59)
        assert isinstance(result, WeatherResult)
        assert result.temperature_c == 25.5
        assert result.precip_prob_pct == 40
        assert result.observed_at == "2025-11-25T10:00:00Z"


def test_weather_falls_back_to_hourly_prob():
    mock_payload = {
        "current": {
            "temperature_2m": 25.5,
            "time": "2025-11-25T10:00:00Z",
        },
        "hourly": {
            "precipitation_probability": [30, 40],
        },
    }
    with patch("src.tools.weather.requests.get", return_value=FakeResponse(mock_payload)):
        result = get_weather(12.97, 77.59)
        assert result.precip_prob_pct == 30


def test_weather_missing_current_raises():
    with patch("src.tools.weather.requests.get", return_value=FakeResponse({})):
        with pytest.raises(ToolError):
            get_weather(12.97, 77.59)


def test_places_limits_to_five_and_scores():
    elements = []
    for idx in range(10):
        elements.append(
            {
                "type": "node",
                "lat": 12.9 + idx * 0.001,
                "lon": 77.5 + idx * 0.001,
                "tags": {
                    "name": f"Place {idx}",
                    "tourism": "attraction",
                    "custom_tag": str(idx),
                },
            }
        )
    with patch("src.tools.places.requests.post", return_value=FakeResponse({"elements": elements})):
        result = get_places(12.97, 77.59)
        assert len(result) == 5
        assert all(isinstance(place, PlaceResult) for place in result)


def test_places_handles_missing_name():
    mock_payload = {
        "elements": [
            {
                "type": "node",
                "lat": 12.9,
                "lon": 77.5,
                "tags": {"tourism": "museum"},
            }
        ]
    }
    with patch("src.tools.places.requests.post", return_value=FakeResponse(mock_payload)):
        result = get_places(12.97, 77.59)
        assert result[0].name == "museum"


def test_places_request_failure_raises():
    with patch(
        "src.tools.places.requests.post",
        side_effect=requests.RequestException("overpass down"),
    ):
        with pytest.raises(ToolError):
            get_places(12.97, 77.59)

