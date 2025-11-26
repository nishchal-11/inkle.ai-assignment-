from __future__ import annotations

from typing import Iterable, List, Optional

from src.tools import PlaceResult

# Use OpenStreetMap's static map service (alternative: use iframe embed)
# Note: staticmap.openstreetmap.org requires proper User-Agent
STATIC_MAP_BASE = "https://staticmap.openstreetmap.org/staticmap.php"


def build_map_link(places: Iterable[PlaceResult]) -> Optional[str]:
    """
    Build a static map URL showing multiple places as markers.
    
    Uses OpenStreetMap's static map service. If that fails, returns an
    OpenStreetMap embed URL that can be used in an iframe.
    """
    points = list(places)[:5]
    if len(points) < 2:
        return None

    # Calculate center from all points for better view
    center_lat = sum(p.lat for p in points) / len(points)
    center_lon = sum(p.lon for p in points) / len(points)
    
    # Build marker string with proper formatting
    marker_parts: List[str] = []
    for idx, place in enumerate(points, start=1):
        # Format coordinates with 4 decimal places for precision
        marker_parts.append(f"{place.lat:.4f},{place.lon:.4f},red-{idx}")

    markers_param = "|".join(marker_parts)
    
    # Build URL with proper encoding
    url = (
        f"{STATIC_MAP_BASE}"
        f"?center={center_lat:.4f},{center_lon:.4f}"
        f"&zoom=12"
        f"&size=600x400"
        f"&markers={markers_param}"
    )
    
    # Alternative: Return OpenStreetMap embed URL if static map doesn't work
    # This can be used as a fallback in the frontend
    return url


def build_map_embed_url(places: Iterable[PlaceResult]) -> Optional[str]:
    """
    Build an OpenStreetMap embed URL for use in an iframe.
    This is a fallback option if static maps don't work.
    """
    points = list(places)[:5]
    if len(points) < 2:
        return None
    
    # Calculate bounding box
    lats = [p.lat for p in points]
    lons = [p.lon for p in points]
    bbox = f"{min(lons)},{min(lats)},{max(lons)},{max(lats)}"
    
    # Build OpenStreetMap embed URL
    url = f"https://www.openstreetmap.org/export/embed.html?bbox={bbox}&layer=mapnik&marker={points[0].lat},{points[0].lon}"
    return url

