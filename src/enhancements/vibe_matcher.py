from __future__ import annotations

from collections import Counter
from typing import Iterable, List, Optional

from src.tools import PlaceResult, WeatherResult

OUTDOOR_KEYWORDS = {"park", "zoo", "national", "lake", "garden", "trail", "wildlife", "beach", "camp"}
CULTURE_KEYWORDS = {"museum", "palace", "temple", "historic", "art", "gallery", "heritage"}
NIGHTLIFE_KEYWORDS = {"bar", "club", "brewery", "pub", "nightlife"}


def generate_vibe_tip(weather: Optional[WeatherResult], places: Iterable[PlaceResult]) -> Optional[str]:
    places = list(places)
    if not places:
        return None

    vibe = _infer_vibe(places)
    if vibe is None and weather is None:
        return None

    recommendations: List[str] = []
    if vibe == "outdoors":
        recommendations.append("Expect plenty of outdoor exploring—wear sturdy shoes.")
    elif vibe == "culture":
        recommendations.append("Cultural hotspots ahead—smart casual layers work well.")
    elif vibe == "nightlife":
        recommendations.append("Nightlife-heavy plan—bring something stylish and comfortable.")

    if weather:
        if weather.precip_prob_pct >= 50:
            recommendations.append("Rain is likely, pack a light raincoat.")
        elif weather.precip_prob_pct >= 30:
            recommendations.append("Carry a compact umbrella just in case.")

        if weather.temperature_c <= 18:
            recommendations.append("It may feel cool, add a warm layer.")
        elif weather.temperature_c >= 30:
            recommendations.append("Heat will be intense, choose breathable fabrics.")

    if not recommendations:
        return None

    return "Tip: " + " ".join(recommendations)


def _infer_vibe(places: List[PlaceResult]) -> Optional[str]:
    vibes = []
    for place in places:
        tags = {value.lower() for value in place.tags.values() if isinstance(value, str)}
        name_tokens = place.name.lower().split()
        tokens = tags.union(name_tokens)
        if tokens & OUTDOOR_KEYWORDS:
            vibes.append("outdoors")
        elif tokens & CULTURE_KEYWORDS:
            vibes.append("culture")
        elif tokens & NIGHTLIFE_KEYWORDS:
            vibes.append("nightlife")

    if not vibes:
        return None

    counts = Counter(vibes)
    priority = ["outdoors", "culture", "nightlife"]
    return max(priority, key=lambda vibe: (counts.get(vibe, 0), -priority.index(vibe)))


