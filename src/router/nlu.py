from __future__ import annotations

import re
from enum import Enum, auto
from typing import Optional, Tuple


class Intent(Enum):
    WEATHER = auto()
    PLACES = auto()
    BOTH = auto()


_WEATHER_KEYWORDS = [
    "weather",
    "temperature",
    "temp",
    "rain",
    "forecast",
    "climate",
    "precip",
]

_PLACES_KEYWORDS = [
    "place",
    "places",
    "trip",
    "plan",
    "visit",
    "itinerary",
    "see",
    "attraction",
    "go",
    "tour",
]


def detect_intent(prompt: str) -> Intent:
    """Classify the user request into weather, places, or both intents."""
    lowered = prompt.lower()
    wants_weather = any(keyword in lowered for keyword in _WEATHER_KEYWORDS)
    wants_places = any(keyword in lowered for keyword in _PLACES_KEYWORDS)

    if wants_weather and wants_places:
        return Intent.BOTH
    if wants_weather:
        return Intent.WEATHER
    if wants_places:
        return Intent.PLACES
    # When uncertain, prefer both so the Parent Agent over-serves rather than under-serves.
    return Intent.BOTH


_LOCATION_PATTERNS = [
    re.compile(r"\bto\s+([A-Za-z][a-zA-Z\s]+)", re.IGNORECASE),
    re.compile(r"\bin\s+([A-Za-z][a-zA-Z\s]+)", re.IGNORECASE),
    re.compile(r"\bfor\s+([A-Za-z][a-zA-Z\s]+)", re.IGNORECASE),
    re.compile(r"\bplan\s+(?:a\s+)?(?:trip\s+to\s+)?([A-Za-z][a-zA-Z\s]+)", re.IGNORECASE),
    re.compile(r"\bvisit\s+([A-Za-z][a-zA-Z\s]+)", re.IGNORECASE),
    re.compile(r"\bgoing\s+to\s+([A-Za-z][a-zA-Z\s]+)", re.IGNORECASE),
    # Pattern for "X escape" or "X trip" - capture X before escape/trip
    re.compile(r"\b([A-Za-z][a-zA-Z\s]+?)\s+(?:escape|trip|vacation|holiday)", re.IGNORECASE),
]

_LOCATION_TRAILING_STOPWORDS = {
    "next",
    "week",
    "weeks",
    "days",
    "day",
    "tomorrow",
    "today",
    "tonight",
    "now",
    "please",
    "soon",
    "asap",
    "escape",
    "getaway",
    "trip",
    "vacation",
    "holiday",
    "plan",
    "visit",
    "going",
    "for",  # "for 10 days" should not be part of location
    # Common pronouns and articles
    "my",
    "me",
    "i",
    "you",
    "your",
    "our",
    "their",
    "his",
    "her",
    "its",
    "the",
    "a",
    "an",
    "this",
    "that",
    "these",
    "those",
    "what",
    "which",
    "who",
    "where",
    "when",
    "how",
    "should",
    "would",
    "could",
    "can",
    "will",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "need",
    "want",
    "know",
}

_NON_LOCATION_TITLES = {
    "Plan",
    "What",
    "Need",
    "Do",
    "I'm",
    "My",
    "Your",
    "Heading",
    "Going",
    "Weather",
    "Trip",
    "Escape",
    "Give",
}

_COMMON_VERBS = {
    "plan",
    "visit",
    "going",
    "go",
    "see",
    "explore",
    "travel",
    "tour",
}

# Add "to" and "go" to stopwords since they're prepositions/directions, not locations
_LOCATION_TRAILING_STOPWORDS.add("to")
_LOCATION_TRAILING_STOPWORDS.add("go")


def extract_location(prompt: str) -> Optional[str]:
    """Attempt to pull a location string out of the user's prompt."""
    # Try pattern-based extraction first (handles "to X", "in X", "for X", "plan X", etc.)
    for pattern in _LOCATION_PATTERNS:
        match = pattern.search(prompt)
        if match:
            candidate = match.group(1).strip()
            # Trim trailing punctuation.
            candidate = re.sub(r"[^\w\s-]", "", candidate)
            candidate_tokens = candidate.split()
            # Remove leading stopwords (like "go" before the actual location)
            while candidate_tokens and candidate_tokens[0].lower() in _LOCATION_TRAILING_STOPWORDS:
                candidate_tokens.pop(0)
            # Remove trailing stopwords
            while candidate_tokens and candidate_tokens[-1].lower() in _LOCATION_TRAILING_STOPWORDS:
                candidate_tokens.pop()
            candidate = " ".join(candidate_tokens)
            if candidate:
                if candidate.islower():
                    candidate = candidate.title()
                return candidate

    # Fallback 1: pick last capitalized word sequence.
    capitalized_chunks = re.findall(r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)", prompt)
    for chunk in reversed(capitalized_chunks):
        if chunk not in _NON_LOCATION_TITLES:
            return chunk

    # Fallback 2: extract all words and find potential location
    # Look for words after common verbs or as standalone location names
    tokens = re.findall(r"[a-zA-Z][a-zA-Z-]*", prompt.lower())
    
    # Filter out stopwords and verbs to get candidate locations
    all_stopwords = _LOCATION_TRAILING_STOPWORDS | _COMMON_VERBS
    
    # Check if there's a word after a common verb
    for i, token in enumerate(tokens):
        if token in _COMMON_VERBS and i + 1 < len(tokens):
            next_token = tokens[i + 1]
            if next_token not in all_stopwords:
                titled = next_token.title()
                if titled not in _NON_LOCATION_TITLES:
                    return titled
    
    # Fallback 3: take the last significant word (not a stopword or verb)
    # But only if we have at least 2 tokens (to avoid false positives like "trip")
    if len(tokens) >= 2:
        for token in reversed(tokens):
            if token not in all_stopwords:
                titled = token.title()
                if titled not in _NON_LOCATION_TITLES:
                    return titled
    
    # Final fallback: for single-word prompts, only accept if it's not a stopword
    # This handles cases like just "mysore" or "bangalore"
    if len(tokens) == 1:
        single_token = tokens[0]
        if single_token not in all_stopwords:
            titled = single_token.title()
            if titled not in _NON_LOCATION_TITLES:
                return titled
    
    return None


def needs_location_clarification(prompt: str) -> bool:
    """Return True when we cannot confidently detect a location."""
    return extract_location(prompt) is None


def plan_tool_sequence(
    prompt: str,
) -> Tuple[Optional[str], Intent]:
    """
    Convenience helper for Phase 1 tests:
    returns (location, intent) that the Parent Agent should use before hitting MCP tools.
    
    Uses Gemini API if available for better NLP understanding, otherwise falls back to regex-based extraction.
    """
    # Try Gemini first for better NLP understanding
    try:
        from .gemini_nlu import extract_intent_and_location_with_gemini
        gemini_location, gemini_intent = extract_intent_and_location_with_gemini(prompt)
        
        # If Gemini successfully extracted both, use it
        if gemini_location and gemini_intent:
            return gemini_location, gemini_intent
        # If Gemini extracted intent but not location, use Gemini intent with regex location
        elif gemini_intent:
            location = extract_location(prompt)
            return location, gemini_intent
    except Exception:
        # If Gemini fails, fall back to regex-based extraction
        pass
    
    # Fallback to regex-based extraction
    location = extract_location(prompt)
    intent = detect_intent(prompt)
    return location, intent
