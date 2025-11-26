from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import List

import requests

from .exceptions import ToolError

# Multiple Overpass API instances for fallback
OVERPASS_INSTANCES = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]


@dataclass
class PlaceResult:
    name: str
    kind: str
    lat: float
    lon: float
    tags: dict

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "lat": self.lat,
            "lon": self.lon,
            "tags": self.tags,
        }


def _build_query(lat: float, lon: float, radius_m: int) -> str:
    """
    Build Overpass query prioritizing tourist attractions and landmarks.
    Queries for high-quality tourism and leisure places.
    """
    template = """
    [out:json][timeout:25];
    (
      // High-priority tourist attractions
      node(around:{radius},{lat},{lon})[tourism=attraction];
      way(around:{radius},{lat},{lon})[tourism=attraction];
      relation(around:{radius},{lat},{lon})[tourism=attraction];
      
      // Museums, galleries, monuments
      node(around:{radius},{lat},{lon})[tourism=museum];
      way(around:{radius},{lat},{lon})[tourism=museum];
      relation(around:{radius},{lat},{lon})[tourism=museum];
      
      node(around:{radius},{lat},{lon})[historic=monument];
      way(around:{radius},{lat},{lon})[historic=monument];
      relation(around:{radius},{lat},{lon})[historic=monument];
      
      node(around:{radius},{lat},{lon})[historic=castle];
      way(around:{radius},{lat},{lon})[historic=castle];
      relation(around:{radius},{lat},{lon})[historic=castle];
      
      node(around:{radius},{lat},{lon})[historic=palace];
      way(around:{radius},{lat},{lon})[historic=palace];
      relation(around:{radius},{lat},{lon})[historic=palace];
      
      // Other tourism types (zoo, theme_park, etc.)
      node(around:{radius},{lat},{lon})[tourism=zoo];
      way(around:{radius},{lat},{lon})[tourism=zoo];
      relation(around:{radius},{lat},{lon})[tourism=zoo];
      
      node(around:{radius},{lat},{lon})[tourism=theme_park];
      way(around:{radius},{lat},{lon})[tourism=theme_park];
      relation(around:{radius},{lat},{lon})[tourism=theme_park];
      
      // Important leisure places (parks, gardens)
      node(around:{radius},{lat},{lon})[leisure=park][name];
      way(around:{radius},{lat},{lon})[leisure=park][name];
      relation(around:{radius},{lat},{lon})[leisure=park][name];
      
      node(around:{radius},{lat},{lon})[leisure=garden][name];
      way(around:{radius},{lat},{lon})[leisure=garden][name];
      relation(around:{radius},{lat},{lon})[leisure=garden][name];
      
      // Other tourism types as fallback
      node(around:{radius},{lat},{lon})[tourism][tourism!=hotel][tourism!=hostel][tourism!=apartment][tourism!=guest_house];
      way(around:{radius},{lat},{lon})[tourism][tourism!=hotel][tourism!=hostel][tourism!=apartment][tourism!=guest_house];
      relation(around:{radius},{lat},{lon})[tourism][tourism!=hotel][tourism!=hostel][tourism!=apartment][tourism!=guest_house];
    );
    out center;
    """
    return template.format(radius=radius_m, lat=lat, lon=lon)


def get_places(
    lat: float,
    lon: float,
    *,
    radius_m: int = 15000,
    limit: int = 5,
    timeout: float = 25.0,
    max_retries: int = 3,
) -> List[PlaceResult]:
    """
    Fetch places using Overpass API with retry logic and fallback instances.
    
    Args:
        lat: Latitude
        lon: Longitude
        radius_m: Search radius in meters
        limit: Maximum number of places to return
        timeout: Request timeout in seconds
        max_retries: Maximum number of retries per instance
    
    Returns:
        List of PlaceResult objects
    
    Raises:
        ToolError: If all instances fail after retries
    """
    query = _build_query(lat, lon, radius_m)
    query_bytes = query.encode("utf-8")
    last_exception = None
    
    # Try each Overpass instance
    for instance_url in OVERPASS_INSTANCES:
        # Retry logic with exponential backoff for each instance
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    instance_url,
                    data=query_bytes,
                    timeout=timeout,
                    headers={"User-Agent": "MultiAgentTourism/1.0 (contact: travel-console@inkle.ai)"},
                )
                response.raise_for_status()
                payload = response.json()
                
                # Success - parse and return results
                return _parse_places_response(payload, lat, lon, limit)
                
            except requests.Timeout:
                last_exception = f"Timeout after {timeout}s"
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    time.sleep(wait_time)
                    continue
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response else None
                if status == 504:  # Gateway Timeout
                    last_exception = f"Gateway timeout (504) from {instance_url}"
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        time.sleep(wait_time)
                        continue
                elif status in (429, 503):  # Rate limit or service unavailable
                    last_exception = f"Service unavailable ({status}) from {instance_url}"
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        time.sleep(wait_time)
                        continue
                else:
                    # For other HTTP errors, try next instance immediately
                    last_exception = f"HTTP {status} from {instance_url}"
                    break
            except requests.RequestException as exc:
                last_exception = f"Network error: {exc}"
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
            except ValueError as exc:
                raise ToolError("Places response was not valid JSON") from exc
    
    # All instances and retries failed
    raise ToolError(
        f"Unable to fetch places after trying {len(OVERPASS_INSTANCES)} instances. "
        f"Last error: {last_exception}. The Overpass API may be temporarily unavailable."
    )


def _parse_places_response(
    payload: dict, lat: float, lon: float, limit: int
) -> List[PlaceResult]:
    """Parse Overpass API response into PlaceResult objects."""

    elements = payload.get("elements", [])
    places: List[PlaceResult] = []
    for element in elements:
        tags = element.get("tags") or {}
        name = tags.get("name")
        if not name:
            name = tags.get("tourism") or tags.get("leisure") or "Point of interest"

        kind = tags.get("tourism") or tags.get("leisure") or "unknown"

        coord = element.get("center") or {
            "lat": element.get("lat"),
            "lon": element.get("lon"),
        }
        lat_val = coord.get("lat")
        lon_val = coord.get("lon")
        if lat_val is None or lon_val is None:
            continue

        places.append(
            PlaceResult(
                name=name,
                kind=kind,
                lat=float(lat_val),
                lon=float(lon_val),
                tags=tags,
            )
        )

    def score(place: PlaceResult) -> float:
        """
        Score places to prioritize high-quality tourist attractions.
        Higher score = better recommendation.
        """
        score = 0.0
        tags = place.tags
        
        # Base score from tag richness (indicates well-documented place)
        score += len(tags) * 0.5
        
        # Prefer places with names, but don't completely exclude nameless places
        if not tags.get("name"):
            score -= 30  # Heavy penalty for places without names
        
        # Tourism type priority (attractions > museums > monuments > others)
        tourism_type = tags.get("tourism", "")
        if tourism_type == "attraction":
            score += 50
        elif tourism_type == "museum":
            score += 45
        elif tourism_type == "zoo":
            score += 40
        elif tourism_type == "theme_park":
            score += 40
        elif tourism_type in ["gallery", "artwork"]:
            score += 35
        elif tourism_type == "viewpoint":
            score += 30
        elif tourism_type in ["hotel", "hostel", "apartment", "guest_house"]:
            score -= 20  # Penalize accommodations when looking for attractions
        
        # Historic sites are highly valuable
        historic = tags.get("historic", "")
        if historic in ["monument", "castle", "palace", "tower", "ruins"]:
            score += 45
        elif historic in ["museum", "memorial"]:
            score += 40
        elif historic:
            score += 30
        
        # Quality indicators
        if tags.get("website"):
            score += 10  # Well-established places have websites
        if tags.get("phone"):
            score += 5
        if tags.get("email"):
            score += 5
        if tags.get("wikidata") or tags.get("wikipedia"):
            score += 15  # Wikipedia presence = notable place
        if tags.get("stars"):
            try:
                stars = int(tags.get("stars", 0))
                score += stars * 3  # Higher rated = better
            except (ValueError, TypeError):
                pass
        
        # Leisure places (parks, gardens) - only if well-documented
        leisure = tags.get("leisure", "")
        if leisure in ["park", "garden"] and tags.get("name"):
            score += 20
            if tags.get("operator") or tags.get("website"):
                score += 10  # Official/maintained parks are better
        
        # Distance penalty (closer is better, but not the main factor)
        distance = _haversine(lat, lon, place.lat, place.lon)
        distance_km = distance / 1000.0
        if distance_km < 5:
            score += 10  # Bonus for very close places
        elif distance_km < 10:
            score += 5
        else:
            score -= distance_km * 0.5  # Penalty for far places
        
        # Avoid generic or low-quality places
        name_lower = place.name.lower()
        if any(word in name_lower for word in ["hostel", "hotel", "apartment", "guest house", "resort"]):
            if tourism_type not in ["attraction", "museum"]:
                score -= 30  # Only keep if it's actually an attraction
        
        return score

    # Calculate scores for all places
    scored_places = [(place, score(place)) for place in places]
    
    # Filter out negative scores and sort by score
    scored_places = [(p, s) for p, s in scored_places if s > 0]
    scored_places.sort(key=lambda x: x[1], reverse=True)
    
    # Extract places in order
    places = [p for p, s in scored_places]
    
    # Remove duplicates by name (keep highest scored)
    seen_names = set()
    unique_places = []
    for place in places:
        name_key = place.name.lower().strip()
        if name_key not in seen_names:
            seen_names.add(name_key)
            unique_places.append(place)
    
    return unique_places[:limit]


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000  # meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c

