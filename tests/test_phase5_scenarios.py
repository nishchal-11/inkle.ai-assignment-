from src.orchestrator import ParentAgentOrchestrator
from src.tools import GeocodeResult, PlaceResult, WeatherResult


def make_orchestrator(weather=True, places=True):
    geocode = GeocodeResult("Bengaluru", 12.97, 77.59, "India")
    weather_result = WeatherResult(temperature_c=24, precip_prob_pct=20, observed_at="now")
    sample_places = [
        ("Bannerghatta National Park", "park"),
        ("Lalbagh Botanical Garden", "park"),
        ("Cubbon Park", "park"),
        ("Bangalore Palace", "museum"),
        ("National Gallery of Modern Art", "museum"),
    ]
    places_result = [
        PlaceResult(
            name=name,
            kind="tourism",
            lat=12.9 + idx * 0.01,
            lon=77.5,
            tags={"name": name, "tourism": kind},
        )
        for idx, (name, kind) in enumerate(sample_places)
    ]

    def fake_geocode(_: str):
        return geocode

    def fake_weather(lat, lon):
        if not weather:
            raise AssertionError("Weather should not be called")
        return weather_result

    def fake_places(lat, lon):
        if not places:
            raise AssertionError("Places should not be called")
        return places_result

    return ParentAgentOrchestrator(
        geocode_tool=fake_geocode,
        weather_tool=fake_weather,
        places_tool=fake_places,
    )


def test_places_only_scenario():
    orchestrator = make_orchestrator(weather=False, places=True)
    response = orchestrator.run("I'm going to Bangalore, plan my trip.")
    assert response.weather is None
    assert len(response.places) == 5
    assert response.vibe_tip
    assert response.map_url


def test_weather_only_scenario():
    orchestrator = make_orchestrator(weather=True, places=False)
    response = orchestrator.run("What is the temperature in Bangalore?")
    assert response.weather is not None
    assert response.places == []


def test_combined_scenario():
    orchestrator = make_orchestrator(weather=True, places=True)
    response = orchestrator.run("Weather and places for Bangalore?")
    assert response.weather is not None
    assert len(response.places) == 5


def test_error_scenario():
    orchestrator = ParentAgentOrchestrator(
        geocode_tool=lambda _: None,
        weather_tool=lambda lat, lon: None,
        places_tool=lambda lat, lon: [],
    )
    response = orchestrator.run("Going to Wakanda.")
    assert response.message == "I don't know this place exists"

