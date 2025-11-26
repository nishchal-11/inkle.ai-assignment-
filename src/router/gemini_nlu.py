from __future__ import annotations

import json
import os
from typing import Optional, Tuple

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from .nlu import Intent


def _get_gemini_client():
    """Initialize and return Gemini client if API key is available."""
    if not GEMINI_AVAILABLE:
        return None
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    
    try:
        genai.configure(api_key=api_key)
        # Try gemini-1.5-pro first for better understanding, fallback to flash for speed
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        return genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"Failed to initialize Gemini client: {e}")
        return None


def extract_intent_and_location_with_gemini(prompt: str) -> Tuple[Optional[str], Optional[Intent]]:
    """
    Use Gemini API to extract location and intent from natural language prompt.
    
    Returns:
        Tuple of (location, intent) where:
        - location: Extracted location name (e.g., "Tamil Nadu", "Mysore", "Paris")
        - intent: Intent enum (WEATHER, PLACES, or BOTH)
    """
    client = _get_gemini_client()
    if not client:
        return None, None
    
    system_prompt = """You are an expert travel assistant specialized in extracting structured information from natural language travel queries.

Your task is to analyze user queries and extract:
1. LOCATION: The specific city, state, region, or country mentioned (extract ONLY the location name - remove words like "escape", "trip", "vacation", "for 10 days", "next month", etc.)
2. INTENT: What the user wants - "weather" (temperature, forecast, climate, rain, precipitation), "places" (attractions, things to see, itinerary, visit, sightseeing, tourist spots), or "both" (comprehensive travel information)

CRITICAL RULES:
- Extract ONLY the location name - no extra words, no time references, no action words
- Normalize location names (e.g., "Tamilnadu" → "Tamil Nadu", "Mumbai" stays "Mumbai")
- If multiple locations mentioned, extract the primary one (usually the destination)
- For intent: "weather" = temperature/forecast/climate queries, "places" = attractions/sightseeing queries, "both" = general travel planning or ambiguous queries
- Default to "both" when intent is unclear or user wants comprehensive information

Return ONLY a valid JSON object with this exact format (NO markdown, NO code blocks, NO explanations, just pure JSON):
{
    "location": "extracted location name or null if not found",
    "intent": "weather" or "places" or "both"
}

Examples:
- "What's the weather in Bangalore?" → {"location": "Bangalore", "intent": "weather"}
- "Plan a Tamilnadu escape for 10 days" → {"location": "Tamil Nadu", "intent": "both"}
- "Show me places to visit in Mysore" → {"location": "Mysore", "intent": "places"}
- "I want to visit Paris and know the weather" → {"location": "Paris", "intent": "both"}
- "Tell me about Kerala" → {"location": "Kerala", "intent": "both"}
- "What's the temperature in New York?" → {"location": "New York", "intent": "weather"}
- "Plan my trip to Goa" → {"location": "Goa", "intent": "places"}
- "I'm planning a 10-day escape to Tamilnadu, what should I know?" → {"location": "Tamil Nadu", "intent": "both"}
- "What's the weather like and what can I see in Mysore?" → {"location": "Mysore", "intent": "both"}
- "Planning a trip to Paris next month, need everything" → {"location": "Paris", "intent": "both"}
- "Temperature forecast for Mumbai" → {"location": "Mumbai", "intent": "weather"}
- "Best attractions in Delhi" → {"location": "Delhi", "intent": "places"}
- "Going to Rajasthan, show me what to see" → {"location": "Rajasthan", "intent": "places"}

Remember: Return ONLY the JSON object, nothing else."""

    try:
        # Configure generation parameters for better JSON output
        generation_config = genai.types.GenerationConfig(
            temperature=0.1,  # Low temperature for more deterministic, structured output
            top_p=0.8,
            top_k=40,
            max_output_tokens=200,  # Limit output to JSON only
        )
        
        # Create the prompt with clear structure
        user_prompt = f"User query: {prompt}\n\nExtract location and intent. Return ONLY JSON:"
        
        response = client.generate_content(
            f"{system_prompt}\n\n{user_prompt}",
            generation_config=generation_config,
        )
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present (handle various formats)
        if "```json" in response_text.lower():
            parts = response_text.split("```json")
            if len(parts) > 1:
                response_text = parts[1].split("```")[0].strip()
        elif "```" in response_text:
            parts = response_text.split("```")
            if len(parts) > 1:
                response_text = parts[1].split("```")[0].strip()
        
        # Try to find JSON in the response (in case there's extra text)
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # Try to fix common JSON issues
                json_str = json_str.replace("'", '"')  # Replace single quotes
                json_str = json_str.replace("None", "null")  # Replace Python None
                data = json.loads(json_str)
            
            location = data.get("location")
            intent_str = data.get("intent", "both").lower().strip()
            
            # Convert intent string to Intent enum
            intent_map = {
                "weather": Intent.WEATHER,
                "places": Intent.PLACES,
                "both": Intent.BOTH,
            }
            intent = intent_map.get(intent_str, Intent.BOTH)
            
            # Clean up and normalize location
            if location:
                location = str(location).strip()
                # Remove common non-location words that might slip through
                location = location.replace("escape", "").replace("trip", "").replace("vacation", "").strip()
                # Normalize common location name variations
                location_normalizations = {
                    "tamilnadu": "Tamil Nadu",
                    "tamil nadu": "Tamil Nadu",
                    "new delhi": "Delhi",
                    "new york city": "New York",
                    "nyc": "New York",
                }
                location_lower = location.lower()
                if location_lower in location_normalizations:
                    location = location_normalizations[location_lower]
                
                if location and location.lower() not in ("null", "none", ""):
                    return location, intent
            
            return None, intent
        
        return None, None
        
    except json.JSONDecodeError as e:
        print(f"Gemini API JSON parsing error: {e}. Response was: {response_text if 'response_text' in locals() else 'N/A'}")
        return None, None
    except Exception as e:
        # If Gemini fails, return None to fall back to regex-based extraction
        print(f"Gemini API error: {e}")
        return None, None

