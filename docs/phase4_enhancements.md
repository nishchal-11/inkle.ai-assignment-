# Phase 4 – Vibe Match & Route Visualization

## 1. Smart “Vibe Match” Packing Assistant

### Data Inputs
- WeatherResult (temp, precipitation probability)
- Places (name, kind, tags)

### Logic
1. Classify each place into high-level vibes:
   - `outdoors`: keywords `park`, `zoo`, `national`, `lake`, `garden`, `trail`, `wildlife`.
   - `culture`: keywords `museum`, `palace`, `temple`, `historic`, `art`.
   - `nightlife`: keywords `bar`, `club`, `brewery`, `pub`.
2. Determine the dominant vibe (by frequency; tie → outdoors > culture > nightlife).
3. Combine vibe with weather heuristics:
   - Temperature < 18 °C → warm layers.
   - Temperature > 30 °C → breathable clothing.
   - Precip ≥ 50 % → rain protection.
4. Return a short actionable sentence, e.g.  
   “Tip: Outdoor-heavy plan with a chance of rain. Pack a light raincoat and trail shoes.”

### Output Contract
`generate_vibe_tip(weather: WeatherResult | None, places: List[PlaceResult]) -> Optional[str]`

## 2. Dynamic Route Visualization

Instead of raw coordinates, build a Static Map URL leveraging OpenStreetMap’s Static API.

Algorithm:
1. Use first place as map center.
2. Build marker string: `lat,lon,color-number`. Example `12.97,77.59,red-1`.
3. Compose URL:  
`https://staticmap.openstreetmap.de/staticmap.php?center={lat},{lon}&zoom=12&size=600x400&markers={markers}`
4. Return `None` when <2 places (not worth mapping).

Function: `build_map_link(places: List[PlaceResult]) -> Optional[str]`

## 3. Integration Points
- After Parent Agent gathers tool data, call `generate_vibe_tip` and `build_map_link` to enrich the response payload.
- UI will render `map_url` as an `<img>` and show `vibe_tip` as footer text.

## 4. Tests
`tests/test_phase4_enhancements.py`
| Test | Purpose |
| --- | --- |
| `test_vibe_tip_outdoor_rainy` | Weather rainy + outdoor places → raincoat suggestion. |
| `test_vibe_tip_hot_cultural` | Hot weather + cultural vibe → breathable clothing tip. |
| `test_map_link_contains_markers` | Map URL includes coordinates for up to 5 places. |
| `test_map_link_returns_none_with_insufficient_places` | When fewer than 2 places, no map link. |

These additions satisfy the “cutting-edge” requirement before frontend implementation.


