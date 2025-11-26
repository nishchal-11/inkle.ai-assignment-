from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.orchestrator import ParentAgentOrchestrator
from src.router import Intent
from src.tools import geocode_city, get_places, get_weather

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

app = FastAPI(
    title="Multi-Agent Tourism Orchestrator",
    description="Routes travel prompts through LangGraph + MCP child agents.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = ParentAgentOrchestrator(
    geocode_tool=geocode_city,
    weather_tool=get_weather,
    places_tool=get_places,
)


class TravelRequest(BaseModel):
    prompt: str
    intent: Optional[Literal["weather", "places", "both"]] = None


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Multi-Agent Tourism Orchestrator is running.",
        "docs": "/docs",
        "travel_endpoint": "/travel",
    }


@app.post("/travel")
def generate_travel_plan(request: TravelRequest):
    forced_intent = None
    if request.intent:
        try:
            forced_intent = Intent[request.intent.upper()]
        except KeyError as exc:
            raise HTTPException(status_code=400, detail="Invalid intent value") from exc

    try:
        result = orchestrator.run(request.prompt, forced_intent=forced_intent)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return result.to_dict()

