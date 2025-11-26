from __future__ import annotations

import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import requests

from .exceptions import ToolError

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Alternative geocoding services (no API key required)
PHOTON_URL = "https://photon.komoot.io/api"
MAPS_CO_URL = "https://geocode.maps.co/search"

# Rate limiting for Nominatim (max 1 request per second)
_last_nominatim_request_time = 0.0


@dataclass
class GeocodeResult:
    name: str
    lat: float
    lon: float
    country: Optional[str]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "country": self.country,
        }


@lru_cache(maxsize=128)
def geocode_city(location: str, *, timeout: float = 10.0) -> Optional[GeocodeResult]:
    """
    Geocode a city name to coordinates using Nominatim API with fallback.
    
    Reads environment variables at runtime:
    - NOMINATIM_USER_AGENT: User-Agent header (required by Nominatim)
    - NOMINATIM_EMAIL: Contact email (required by Nominatim)
    """
    # Read environment variables at runtime to ensure they're current
    user_agent = os.getenv(
        "NOMINATIM_USER_AGENT",
        "MultiAgentTourism/1.0 (contact: travel-console@inkle.ai)",
    )
    contact_email = os.getenv("NOMINATIM_EMAIL", "travel-console@inkle.ai")
    
    # Try Nominatim first
    try:
        return _query_geocoder(NOMINATIM_URL, location, timeout, user_agent, contact_email)
    except requests.HTTPError as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in {403, 429}:
            # Nominatim blocked us, try Photon (Komoot's geocoding service, no API key needed)
            try:
                return _query_photon_geocoder(location, timeout, user_agent)
            except requests.RequestException as photon_exc:
                # Last resort: try maps.co (may require API key)
                try:
                    return _query_geocoder(MAPS_CO_URL, location, timeout, user_agent, contact_email)
                except requests.RequestException as fallback_exc:
                    raise ToolError(
                        f"Geocoding failed: All services unavailable. "
                        f"Last error: {str(photon_exc)}. "
                        f"Please ensure NOMINATIM_USER_AGENT and NOMINATIM_EMAIL environment variables are set correctly."
                    ) from fallback_exc
        raise ToolError(f"Geocoding request failed: {exc}") from exc
    except requests.RequestException as exc:
        raise ToolError(f"Geocoding request failed: {exc}") from exc
    except ValueError as exc:
        raise ToolError("Geocoding response was not valid JSON") from exc


def _query_geocoder(
    base_url: str, location: str, timeout: float, user_agent: str, contact_email: str
) -> Optional[GeocodeResult]:
    """Query a geocoding API with rate limiting for Nominatim."""
    global _last_nominatim_request_time
    
    # Rate limiting for Nominatim (max 1 request per second)
    if "nominatim" in base_url.lower():
        current_time = time.time()
        time_since_last = current_time - _last_nominatim_request_time
        if time_since_last < 1.0:
            time.sleep(1.0 - time_since_last)
        _last_nominatim_request_time = time.time()
    
    params = {
        "q": location,
        "format": "json",
        "limit": 1,
    }
    if contact_email and "nominatim" in base_url.lower():
        params["email"] = contact_email
    
    headers = {"User-Agent": user_agent}
    response = requests.get(base_url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    if not data:
        return None

    first = data[0]
    lat = float(first["lat"])
    lon = float(first["lon"])
    display_name = first.get("display_name") or location
    country = first.get("address", {}).get("country")
    return GeocodeResult(name=display_name, lat=lat, lon=lon, country=country)


def _query_photon_geocoder(location: str, timeout: float, user_agent: str) -> Optional[GeocodeResult]:
    """
    Query Photon geocoding service (Komoot's open geocoding API).
    No API key required, good fallback for Nominatim.
    """
    params = {
        "q": location,
        "limit": 1,
    }
    headers = {"User-Agent": user_agent}
    response = requests.get(PHOTON_URL, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    
    # Handle both dict and list responses
    if isinstance(data, list):
        features = data
    else:
        features = data.get("features", [])
    if not features:
        return None
    
    first = features[0]
    
    # Photon API returns GeoJSON format
    if isinstance(first, dict) and "geometry" in first:
        geometry = first.get("geometry", {})
        coordinates = geometry.get("coordinates", [])
        if len(coordinates) < 2:
            return None
        lon = float(coordinates[0])
        lat = float(coordinates[1])
        properties = first.get("properties", {})
        display_name = properties.get("name") or properties.get("display_name") or location
        country = properties.get("country")
    else:
        # Fallback for other formats
        lat = float(first.get("lat", 0))
        lon = float(first.get("lon", 0))
        display_name = first.get("name") or first.get("display_name") or location
        country = first.get("country")
    
    return GeocodeResult(name=display_name, lat=lat, lon=lon, country=country)

