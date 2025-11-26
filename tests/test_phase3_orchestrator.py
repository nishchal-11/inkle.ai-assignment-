from dataclasses import dataclass
from typing import List

import pytest

from src.orchestrator import OrchestratorResponse, ParentAgentOrchestrator
from src.router import Intent
from src.tools import GeocodeResult, PlaceResult, ToolError, WeatherResult


@dataclass
class DummyWeather(WeatherResult):
    pass


@dataclass
class DummyPlace(PlaceResult):
    pass


def make_orchestrator(
    *,
    geocode_return: GeocodeResult | None = GeocodeResult("Bengaluru", 12.97, 77.59, "India"),
    weather_result: WeatherResult | Exception = WeatherResult(24.0, 30, "now"),
    places_result: List[PlaceResult] | Exception = None,
) -> ParentAgentOrchestrator:
    if places_result is None:
        places_result = [
            PlaceResult(name=f"Place {i}", kind="tourism", lat=12.9 + i * 0.01, lon=77.5, tags={"name": f"Place {i}"})
            for i in range(5)
        ]

    def fake_geocode(_: str):
        return geocode_return

    def fake_weather(lat: float, lon: float):
        if isinstance(weather_result, Exception):
            raise weather_result
        return weather_result

    def fake_places(lat: float, lon: float):
        if isinstance(places_result, Exception):
            raise places_result
        return places_result

    return ParentAgentOrchestrator(
        geocode_tool=fake_geocode,
        weather_tool=fake_weather,
        places_tool=fake_places,
    )


def test_weather_only_flow(monkeypatch):
    orchestrator = make_orchestrator()
    response = orchestrator.run("What is the weather in Bangalore?")
    assert isinstance(response, OrchestratorResponse)
    assert response.weather is not None
    assert response.places == []


def test_places_only_flow():
    orchestrator = make_orchestrator()
    response = orchestrator.run("Plan my trip to Bangalore")
    assert len(response.places) == 5
    assert response.weather is None


def test_both_flow():
    orchestrator = make_orchestrator()
    response = orchestrator.run("Weather and places for Bangalore?")
    assert response.weather is not None
    assert len(response.places) == 5
    assert response.vibe_tip is not None
    assert response.map_url is not None


def test_missing_location_message():
    orchestrator = make_orchestrator()
    response = orchestrator.run("Plan my trip")
    assert response.message.startswith("Could you tell me")
    assert response.errors["location"] == "missing"


def test_invalid_location_message():
    orchestrator = make_orchestrator(geocode_return=None)
    response = orchestrator.run("Plan my trip to Atlantis")
    assert response.message == "I don't know this place exists"
    assert response.errors["geocode"] == "not_found"


def test_weather_error_does_not_block_places():
    orchestrator = make_orchestrator(weather_result=ToolError("weather down"))
    response = orchestrator.run("Weather and places for Bangalore?")
    assert response.weather is None
    assert "weather" in response.errors
    assert len(response.places) == 5


def test_places_error_does_not_block_weather():
    orchestrator = make_orchestrator(places_result=ToolError("places down"))
    response = orchestrator.run("Weather and places for Bangalore?")
    assert response.places == []
    assert "places" in response.errors
    assert response.weather is not None


def test_forced_intent_override():
    orchestrator = make_orchestrator()
    response = orchestrator.run("Plan my trip to Bangalore", forced_intent=Intent.WEATHER)
    assert response.weather is not None
    assert response.places == []

