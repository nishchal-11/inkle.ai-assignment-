# Phase 1 – System Architecture & Conversation Flow

## 1. Conversational Routing Overview
1. User submits a free-form travel prompt via the UI.
2. **Parent Agent (Gemini via LangGraph+MCP)** receives the prompt with the system instruction defined below.
3. Parent Agent performs lightweight NLU:
   - Extract `location_candidate` (city or region tokens).
   - Detect `intent` ∈ {`weather`, `places`, `both`}. If ambiguous, prefer `both`.
4. Parent Agent calls the MCP-exposed `geocode_city` helper to validate the location and fetch coordinates.
5. If `geocode_city` returns `None`, Parent Agent reply: “I don't know this place exists” (verbatim).
6. If the user asked for weather, Parent Agent calls `get_weather`.
7. If the user asked for attractions, Parent Agent calls `get_places`.
8. Parent Agent merges tool payloads, runs Vibe Match + Map prep hooks (Phase 4), then formats the natural language response for the frontend.

### LangGraph Nodes
- **Input Node** → validates payload shape from the frontend (`{ user_id, prompt, locale }`).
- **Router Node (Parent Agent)** → Gemini model with system prompt, handles tool selection.
- **Tool Nodes (MCP servers)** → `geocode_city`, `get_weather`, `get_places`.
- **Post-Processing Node** → synthesizes Vibe Match tips & map info once Phases 2–4 are ready.
- **Output Node** → returns structured response for UI: `{ weatherBlock?, placesBlock?, vibeTip?, mapEmbed? }`.

## 2. Tool Definitions (MCP-Compliant)

### 2.1 Geocoding Helper – `geocode_city`
- **Input**: `{ "location": "Bangalore" }`
- **Process**: call Nominatim `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=<location>`.
- **Output**:
  ```json
  {
    "name": "Bangalore",
    "lat": 12.9716,
    "lon": 77.5946,
    "country": "India"
  }
  ```
- **On failure**: return `null` (Parent handles messaging).

### 2.2 Weather Tool – `get_weather`
- **Input**: `{ "lat": 12.97, "lon": 77.59 }`
- **Process**: Open-Meteo `https://api.open-meteo.com/v1/forecast?latitude=<lat>&longitude=<lon>&current=temperature_2m,precipitation_probability&hourly=precipitation_probability`.
- **Output**:
  ```json
  {
    "temperature_c": 24.1,
    "precip_prob_pct": 35,
    "observed_at": "2025-11-25T10:00:00Z"
  }
  ```

### 2.3 Places Tool – `get_places`
- **Input**: `{ "lat": 12.97, "lon": 77.59, "radius_m": 15000 }`
- **Process**: Overpass QL query selecting nodes/ways/relations tagged `tourism=*` OR `leisure=*`.
- **Output**:
  ```json
  {
    "places": [
      {
        "name": "Bangalore Palace",
        "type": "tourism",
        "lat": 12.998,
        "lon": 77.592,
        "tags": ["historic", "palace"]
      },
      "... up to 5 results ..."
    ]
  }
  ```
- **Filtering**: Score by tag richness + distance; truncate to 5.

## 3. Error Logic
- `geocode_city` returns `null` → Parent outputs **exact** phrase: “I don't know this place exists”.
- Weather API failure (HTTP/timeout) → Parent apologizes and surfaces only attractions (if any); message: “Weather data unavailable right now.”
- Places API failure → Parent shares weather only; message: “Couldn't fetch attractions at the moment.”
- Both tool failures → Parent surfaces graceful fallback: “I ran into an issue fetching travel data.”
- Parent always logs the raw error for observability (Phase 5 instrumentation).

## 4. Parent Agent System Prompt (Gemini via MCP)
```
You are a Tourism Assistant. You have access to tools: geocode_city,
get_weather, get_places. Always call geocode_city first to validate the
location. If the user asks for weather, use get_weather. If they ask for
attractions, use get_places. If they ask for both, use both. If geocode_city
returns null, reply exactly with: "I don't know this place exists". Combine
tool outputs into a concise travel brief plus actionable packing tip when data
allows. When in doubt about intent, provide both weather and places.
```

## 5. Unit Test Plan for Phase 1
We can implement these immediately with plain Python tests (no API calls):

| Test | Purpose | Method |
| --- | --- | --- |
| `test_router_detects_weather_only_intent` | Ensure NLU classifies prompts like “What’s the temperature in Bangalore?” as `weather`. | Stub Gemini reasoning with deterministic function or regex and assert router state. |
| `test_router_detects_places_only_intent` | Prompts like “Plan my trip to Bangalore” → `places`. | Same stub approach. |
| `test_router_detects_both_intent` | Prompts containing both weather + attractions keywords route to both. | Assert combined intent. |
| `test_router_handles_missing_location` | Input lacking a recognizable location triggers clarification before API call. | Assert router asks user for location string. |
| `test_router_handles_invalid_location_error` | When `geocode_city` mock returns `None`, response equals “I don't know this place exists”. | Mock tool + verify output. |
| `test_router_tool_sequence` | Ensure geocode is always invoked before other tools, even if intent is weather-only. | Inspect recorded call order. |

Each test will be part of `tests/test_phase1_router.py` with mocked MCP tool handles so they run without network access.

---
Phase 1 deliverables (this document + upcoming test skeleton) provide the foundation for coding in subsequent phases. Once approved, we can scaffold the actual router logic and its tests.


