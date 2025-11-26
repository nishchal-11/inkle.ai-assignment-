# Phase 3 – Parent Agent Orchestration

## 1. Components
- **Gemini LLM (via Google Generative AI SDK)** – executes the Parent Agent reasoning inside LangGraph.
- **MCP Tool Servers** – wrap `geocode_city`, `get_weather`, `get_places` so LangGraph tool nodes can call them in a sandboxed runtime.
- **LangGraph Router** – state machine that decides which tools to call and merges results.
- **Post Processor** – converts tool data into structured UI payload `{weatherBlock, placesBlock, vibeInputs}`.

## 2. System Prompt (final)
```
You are a Tourism Assistant. Tools: geocode_city, get_weather, get_places.
Always start by calling geocode_city with the user's location. If it returns
null, reply exactly: "I don't know this place exists". If the user wants
weather, call get_weather. If they want attractions, call get_places. If they
ask for both or the intent is unclear, call both. Present concise natural
language summaries plus structured JSON fields for the UI, and pass along the
raw tool data so downstream modules can craft packing tips and route maps.
```

## 3. LangGraph Plan
State shape (TypedDict):
```python
class RouterState(TypedDict, total=False):
    prompt: str
    location: str
    intent: Literal["weather", "places", "both"]
    coords: tuple[float, float]
    weather: WeatherResult | None
    places: list[PlaceResult]
    message: str
```

Graph edges:
1. **Entry Node** – populate `prompt`, run `nlu.plan_tool_sequence`.
2. **Geocode Node** – call MCP `geocode_city`.
3. **Decision Node** – branch to weather / places / both / final.
4. **Weather Node** – call `get_weather`; capture ToolError.
5. **Places Node** – call `get_places`; capture ToolError.
6. **Assembler Node** – merge data, inject defaults when some tools fail.

## 4. MCP Binding
- Each tool module exposes `to_mcp_tool()` returning metadata (name, input schema, Python callable). Wrapper ensures the HTTP logic from Phase 2 is reused.
- Parent agent runs inside LangGraph server and references the Gemini API key via `GEMINI_API_KEY` environment variable.

## 5. Unit Tests for Phase 3
Located in `tests/test_phase3_orchestrator.py`. Tests stub tool functions / llm to avoid network:
| Test | Purpose |
| --- | --- |
| `test_run_returns_weather_only` | Ensure orchestrator only calls weather tool when intent == `weather`. |
| `test_run_returns_places_only` | Ensures geocode + places flow, verifies 5-place limit preserved. |
| `test_run_handles_invalid_location` | When geocode returns `None`, message equals the mandated text. |
| `test_run_handles_missing_location_in_prompt` | Router requests clarification message. |
| `test_run_handles_tool_errors` | Weather failure should not block places data and vice versa. |

These tests give us confidence before wiring LangGraph + MCP for real tool execution.


