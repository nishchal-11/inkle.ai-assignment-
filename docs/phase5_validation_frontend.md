# Phase 5 – Testing & Frontend Plan

## 1. Scenario Validation
Automated tests will simulate the four required prompts using mocked tools so they are deterministic.

### Test Matrix
| Scenario | Prompt | Expected |
| --- | --- | --- |
| Places Only | “I'm going to Bangalore, plan my trip.” | 5 attractions, vibe tip present, map URL present, weather omitted. |
| Weather Only | “What is the temperature in Bangalore?” | Weather block with `XX°C`, no places. |
| Combined | “Weather and places for Bangalore?” | Both weather + places blocks plus vibe tip & map. |
| Error | “Going to Wakanda.” | Message “I don't know this place exists”. |

Implementation: `tests/test_phase5_scenarios.py` using `ParentAgentOrchestrator` with fake tool outputs to validate formatting.

## 2. Frontend Blueprint (React + Vite)
- **Stack**: React 18 + TypeScript + Tailwind + Framer Motion for animations.
- **Layout**:
  - Hero section with radial gradient background, glassmorphic chat card.
  - Input area with intent chips (“Weather”, “Places”, “Both”) that highlight based on detected intent.
  - Response cards for Weather, Places, Vibe Tip, and Static Map preview.
- **Animations**:
  - Tool call timeline animates as Parent Agent routes requests.
  - Cards fade/slide in sequentially when data arrives.
- **Map Embed**: `<img src={mapUrl} />` plus “Open in OSM” button.
- **Packing Assistant**: color-coded pill that surfaces the vibe tip with emoji indicating vibe (e.g., 🌿 for outdoors).

## 3. Frontend Data Contract
API response shape from backend:
```ts
type TravelResponse = {
  message: string;
  weather?: {
    temperature_c: number;
    precip_prob_pct: number;
    observed_at: string;
  };
  places?: Array<{
    name: string;
    kind: string;
    lat: number;
    lon: number;
  }>;
  vibe_tip?: string;
  map_url?: string;
  errors?: Record<string, string>;
};
```

## 4. Manual QA Checklist
- Submit the four key prompts against the live backend.
- Ensure vibe tip reflects weather/places context.
- Confirm map renders pins for up to five places.
- Validate error styling uses the mandated text.


