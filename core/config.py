"""Application constants and default configuration."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List

APP_NAME = "Personalized Travel Itinerary Planner"
APP_TAGLINE = "Plan less. Wander more."

GEMINI_MODELS: List[str] = ["gemini-1.5-flash", "gemini-1.5-pro"]
GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"
GROQ_FALLBACK_MODEL = "openai/gpt-oss-20b"
GROQ_MODELS: List[str] = [GROQ_DEFAULT_MODEL, GROQ_FALLBACK_MODEL]
PROVIDERS: List[str] = ["Gemini", "Groq", "Demo Mode (no key needed)"]

SUPPORTED_CURRENCIES: List[str] = ["USD", "INR"]
EXCHANGE_RATES_TO_USD: Dict[str, float] = {
    "USD": 1.0,
    "INR": 0.012,
    "EUR": 1.08,
    "GBP": 1.27,
    "THB": 0.027,
    "JPY": 0.0067,
    "IDR": 0.000063,
}
USD_TO_INR = 83.0

VIBES = ["Beach", "Mountains", "Cultural", "Urban", "Wildlife", "Wellness"]
BUDGET_LEVELS = ["Budget", "Moderate", "Luxury"]
PARTIES = ["Solo", "Couple", "Family", "Friends"]
PACES = ["Relaxed", "Moderate", "Fast-Paced"]
INTERESTS = [
    "Food", "Adventure", "History", "Nightlife", "Shopping",
    "Nature", "Art", "Photography",
]
DIETS = ["Any", "Vegetarian", "Vegan", "Halal", "Jain"]


class BudgetLevel(str, Enum):
    """Supported trip budget tiers."""

    BUDGET = "Budget"
    MODERATE = "Moderate"
    LUXURY = "Luxury"


SESSION_PREFERENCES = "trip_preferences"
SESSION_PROVIDER = "llm_provider"
SESSION_MODEL = "llm_model"
SESSION_API_KEY = "llm_api_key"
SESSION_ITINERARY = "current_itinerary"
SESSION_SAVED_TRIP_ID = "current_saved_trip_id"
SESSION_RECOMMENDATIONS = "recommendations"
SESSION_ACTIVE_TAB = "active_tab"
SESSION_INITIALIZED = "_state_initialized"

DEFAULT_DAYS = 3
MIN_DAYS = 1
MAX_DAYS = 14
