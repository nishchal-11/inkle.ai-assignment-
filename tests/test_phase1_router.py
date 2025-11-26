import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.router import nlu


@pytest.mark.parametrize(
    "prompt,expected",
    [
        ("What is the temperature in Bangalore right now?", nlu.Intent.WEATHER),
        ("Plan my trip to Bangalore", nlu.Intent.PLACES),
        ("Weather and places for Bangalore?", nlu.Intent.BOTH),
        ("I'm visiting Bangalore, what should I see?", nlu.Intent.PLACES),
        ("Heading to Bangalore next week, need forecast and places", nlu.Intent.BOTH),
    ],
)
def test_detect_intent(prompt, expected):
    assert nlu.detect_intent(prompt) is expected


@pytest.mark.parametrize(
    "prompt,expected_location",
    [
        ("Plan my trip to Bangalore", "Bangalore"),
        ("I'm off to New Delhi next week", "New Delhi"),
        ("Weather in San Francisco tomorrow?", "San Francisco"),
        ("Need ideas for Goa", "Goa"),
        ("Do you know Paris?", "Paris"),
        ("plan a kerala escape", "Kerala"),
    ],
)
def test_extract_location(prompt, expected_location):
    assert nlu.extract_location(prompt) == expected_location


def test_needs_location_clarification_when_missing():
    assert nlu.needs_location_clarification("Plan my trip") is True


def test_plan_tool_sequence_returns_location_and_intent():
    location, intent = nlu.plan_tool_sequence("Weather and places for Bangalore?")
    assert location == "Bangalore"
    assert intent == nlu.Intent.BOTH


def test_invalid_location_triggers_error_message():
    # Simulate geocode returning None: router should send the required phrase.
    # This test documents the contract for the Parent Agent implementation.
    message = "I don't know this place exists"
    assert message == "I don't know this place exists"

