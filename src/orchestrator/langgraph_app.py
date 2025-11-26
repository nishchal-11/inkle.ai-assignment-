from __future__ import annotations

from typing import Any, Dict

from src.router import Intent, plan_tool_sequence
from src.tools import geocode_city, get_places, get_weather

try:
    from langgraph.graph import END, START, StateGraph
    from langgraph.graph.message import add_messages
except ImportError:  # pragma: no cover
    StateGraph = None
    END = None
    START = None


class RouterState(dict):
    """Simple dict-based state for LangGraph; populated incrementally."""


def build_langgraph_app() -> Any:
    """
    Creates the LangGraph application wiring prompts to MCP tools.
    Raises ImportError if langgraph is not installed (so unit tests can still run).
    """

    if StateGraph is None:
        raise ImportError("langgraph is not installed; install langgraph to run the full graph.")

    graph = StateGraph(dict)

    def entry_node(state: Dict[str, Any]) -> Dict[str, Any]:
        location, intent = plan_tool_sequence(state["prompt"])
        state["location"] = location
        state["intent"] = intent
        return state

    def geocode_node(state: Dict[str, Any]) -> Dict[str, Any]:
        result = geocode_city(state["location"])
        state["geocode"] = result
        return state

    def weather_node(state: Dict[str, Any]) -> Dict[str, Any]:
        geocode = state["geocode"]
        state["weather"] = get_weather(geocode.lat, geocode.lon)
        return state

    def places_node(state: Dict[str, Any]) -> Dict[str, Any]:
        geocode = state["geocode"]
        state["places"] = get_places(geocode.lat, geocode.lon)
        return state

    def assembler_node(state: Dict[str, Any]) -> Dict[str, Any]:
        return state

    graph.add_node("entry", entry_node)
    graph.add_node("geocode", geocode_node)
    graph.add_node("weather", weather_node)
    graph.add_node("places", places_node)
    graph.add_node("assembler", assembler_node)

    graph.add_edge(START, "entry")
    graph.add_edge("entry", "geocode")

    def decide_branch(state: Dict[str, Any]):
        intent = state["intent"]
        if intent == Intent.WEATHER:
            return "weather"
        if intent == Intent.PLACES:
            return "places"
        return "weather"

    graph.add_conditional_edges(
        "geocode",
        decide_branch,
        {
            "weather": "weather",
            "places": "places",
        },
    )

    graph.add_edge("weather", "places")
    graph.add_edge("places", "assembler")
    graph.add_edge("assembler", END)

    return graph.compile()


