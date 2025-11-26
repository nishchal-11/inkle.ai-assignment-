from src.enhancements import build_map_link, generate_vibe_tip
from src.tools import PlaceResult, WeatherResult


def make_place(name: str, kind: str, tags: dict, lat=12.97, lon=77.59):
    return PlaceResult(name=name, kind=kind, lat=lat, lon=lon, tags=tags)


def test_vibe_tip_outdoor_rainy():
    weather = WeatherResult(temperature_c=22, precip_prob_pct=70, observed_at="now")
    places = [
        make_place("Bannerghatta National Park", "tourism", {"name": "Bannerghatta National Park"}),
        make_place("Lalbagh Botanical Garden", "tourism", {"name": "Botanical Garden"}),
    ]
    tip = generate_vibe_tip(weather, places)
    assert tip is not None
    assert "raincoat" in tip.lower()
    assert "outdoor" in tip.lower() or "sturdy" in tip.lower()


def test_vibe_tip_hot_cultural():
    weather = WeatherResult(temperature_c=33, precip_prob_pct=10, observed_at="now")
    places = [
        make_place("Bangalore Palace", "tourism", {"name": "Bangalore Palace", "historic": "yes"}),
        make_place("National Gallery of Modern Art", "tourism", {"name": "Art Gallery"}),
    ]
    tip = generate_vibe_tip(weather, places)
    assert tip is not None
    assert "breathable" in tip.lower()


def test_map_link_contains_markers():
    places = [
        make_place(f"Place {i}", "tourism", {"name": f"Place {i}"}, lat=12.9 + i * 0.01, lon=77.5 + i * 0.01)
        for i in range(3)
    ]
    url = build_map_link(places)
    assert url is not None
    assert "staticmap" in url
    assert "markers=" in url
    assert "Place" not in url  # only coordinates


def test_map_link_requires_multiple_places():
    place = make_place("Solo", "tourism", {"name": "Solo"})
    assert build_map_link([place]) is None


