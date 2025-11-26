from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from src.enhancements import build_map_link, generate_vibe_tip
from src.router import Intent, needs_location_clarification, plan_tool_sequence
from src.tools import GeocodeResult, PlaceResult, ToolError, WeatherResult


@dataclass
class OrchestratorResponse:
    message: str
    location: Optional[str]
    intent: str
    weather: Optional[WeatherResult]
    places: List[PlaceResult]
    errors: Dict[str, str]
    vibe_tip: Optional[str] = None
    map_url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "location": self.location,
            "intent": self.intent,
            "weather": self.weather.to_dict() if self.weather else None,
            "places": [place.to_dict() for place in self.places],
            "errors": self.errors,
            "vibe_tip": self.vibe_tip,
            "map_url": self.map_url,
        }


ToolFn = Callable[..., object]


class ParentAgentOrchestrator:
    """
    Deterministic orchestrator that mirrors the LangGraph logic but is simple enough for unit tests.
    """

    def __init__(
        self,
        *,
        geocode_tool: Callable[[str], Optional[GeocodeResult]],
        weather_tool: Callable[[float, float], WeatherResult],
        places_tool: Callable[[float, float], List[PlaceResult]],
    ) -> None:
        self._geocode = geocode_tool
        self._weather = weather_tool
        self._places = places_tool

    def run(self, prompt: str, *, forced_intent: Optional[Intent] = None) -> OrchestratorResponse:
        if needs_location_clarification(prompt):
            return OrchestratorResponse(
                message="Could you tell me which city or region you're referring to?",
                location=None,
                intent="unknown",
                weather=None,
                places=[],
                errors={"location": "missing"},
            )

        location, intent = plan_tool_sequence(prompt)
        if forced_intent:
            intent = forced_intent
        intent_str = intent.name.lower()
        geocode = self._geocode(location)
        if geocode is None:
            return OrchestratorResponse(
                message="I don't know this place exists",
                location=location,
                intent=intent_str,
                weather=None,
                places=[],
                errors={"geocode": "not_found"},
            )

        weather_result: Optional[WeatherResult] = None
        places_result: List[PlaceResult] = []
        errors: Dict[str, str] = {}

        if intent in (Intent.WEATHER, Intent.BOTH):
            try:
                weather_result = self._weather(geocode.lat, geocode.lon)
            except ToolError as exc:
                errors["weather"] = str(exc)

        if intent in (Intent.PLACES, Intent.BOTH):
            try:
                places_result = self._places(geocode.lat, geocode.lon)
            except ToolError as exc:
                errors["places"] = str(exc)

        summary = self._format_summary(geocode.name, weather_result, places_result, errors)
        vibe_tip = generate_vibe_tip(weather_result, places_result)
        map_url = build_map_link(places_result)
        return OrchestratorResponse(
            message=summary,
            location=geocode.name,
            intent=intent_str,
            weather=weather_result,
            places=places_result,
            errors=errors,
            vibe_tip=vibe_tip,
            map_url=map_url,
        )

    @staticmethod
    def _format_summary(
        location_name: str,
        weather: Optional[WeatherResult],
        places: List[PlaceResult],
        errors: Dict[str, str],
    ) -> str:
        sections: List[str] = [f"Here's what I found for {location_name}:"]
        if weather:
            sections.append(
                f"- Weather: {weather.temperature_c:.0f}°C with {weather.precip_prob_pct}% chance of precipitation."
            )
        elif "weather" in errors:
            sections.append("- Weather data unavailable right now.")

        if places:
            names = ", ".join(place.name for place in places[:5])
            sections.append(f"- Places: {names}.")
        elif "places" in errors:
            sections.append("- Couldn't fetch attractions at the moment.")

        return " ".join(sections)

