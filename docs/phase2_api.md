# Phase 2 – API Integration (Helper + Child Agents)

This document captures how each MCP tool will call external services plus the validation logic we must cover with unit tests.

## 1. Shared Conventions
- HTTP client: `requests`, timeout default 10 s.
- Headers: include `User-Agent: MultiAgentTourism/1.0 (contact@example.com)` to satisfy OpenStreetMap policies.
- Errors: wrap unexpected responses in `ToolError` (custom exception) so LangGraph can branch.
- Return types: small dataclasses serialized to dicts before MCP return.

## 2. Geocoding Helper – `geocode_city`
- Endpoint: `GET https://nominatim.openstreetmap.org/search`
- Query params: `q`, `format=json`, `limit=1`.
- Response handling:
  - Pick the first entry, parse `lat`, `lon`, `display_name`.
  - Return `GeocodeResult(name, lat, lon, country_code)`.
  - If the array is empty → return `None` (constructed in Python as `Optional[GeocodeResult]`).
- Errors:
  - Network exceptions/timeouts → raise `ToolError("Geocoding request failed")`.
  - Invalid JSON → same error.

## 3. Weather Tool – `get_weather`
- Endpoint: `GET https://api.open-meteo.com/v1/forecast`
- Params: `latitude`, `longitude`, `current=temperature_2m,precipitation,precipitation_probability`.
- Response:
  - Use `current["temperature_2m"]` as Celsius.
  - Use `current.get("precipitation_probability")` else fallback to the first value of `hourly["precipitation_probability"]`.
  - Return payload:
    ```json
    {
      "temperature_c": float,
      "precip_prob_pct": int,
      "observed_at": iso8601 string
    }
    ```
- Errors:
  - Missing `current` data → `ToolError("Weather data unavailable")`.

## 4. Places Tool – `get_places`
- Endpoint: `POST https://overpass-api.de/api/interpreter`
- Query template:
  ```
  [out:json][timeout:25];
  (
    node(around:{radius},{lat},{lon})[tourism];
    way(around:{radius},{lat},{lon})[tourism];
    relation(around:{radius},{lat},{lon})[tourism];
    node(around:{radius},{lat},{lon})[leisure];
    way(around:{radius},{lat},{lon})[leisure];
    relation(around:{radius},{lat},{lon})[leisure];
  );
  out center;
  ```
- Processing:
  - Convert each element to `PlaceResult(name, kind, lat, lon, tags)`.
  - Score by `(number of tags, has name, distance)`; take top 5.
  - If `name` missing, synthesize from `tags.get("tourism")`/`tags.get("leisure")`.

## 5. Unit Test Strategy (Phase 2)

| Test | Module | Description |
| --- | --- | --- |
| `test_geocode_success` | `geocode_city` | Mock Nominatim JSON, verify dataclass fields. |
| `test_geocode_empty` | `geocode_city` | Empty list returns `None`. |
| `test_weather_parsing` | `get_weather` | Ensure temperature/prob extraction and fallback hourly precipitation. |
| `test_weather_missing_current` | `get_weather` | Raises `ToolError`. |
| `test_places_limits_to_five` | `get_places` | Provide >5 entries; assert 5 returned sorted by score. |
| `test_places_handles_missing_names` | `get_places` | Ensures fallback title from tag. |
| `test_places_request_failure` | `get_places` | Network error raises `ToolError`. |

Tests live in `tests/test_phase2_tools.py` using `unittest.mock.patch` to fake `requests.get/post`.

With this blueprint, we can confidently wire MCP bindings in Phase 3.


