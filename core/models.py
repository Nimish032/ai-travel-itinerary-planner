"""Typed Pydantic models shared by the planner."""

from __future__ import annotations

from datetime import date as date_type, datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class TripPreferences(BaseModel):
    """User preferences used to recommend and plan a trip."""

    model_config = ConfigDict(extra="ignore")

    destination: Optional[str] = None
    vibes: List[str] = Field(default_factory=list)
    days: int = Field(default=3, ge=1, le=14)
    start_date: Optional[date_type] = None
    budget_level: str = "Moderate"
    party: str = "Solo"
    travelers: int = Field(default=1, ge=1, le=50)
    pace: str = "Moderate"
    interests: List[str] = Field(default_factory=list)
    diet: str = "Any"
    home_currency: str = "USD"


class DestinationRecommendation(BaseModel):
    """A destination suggestion returned by a recommendation provider."""

    city: str
    country: str
    match_score: int = Field(ge=0, le=100)
    best_season: str
    avg_temp_c: float
    est_daily_cost_usd: float = Field(ge=0)
    highlight_tags: List[str] = Field(default_factory=list)
    why_it_matches: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class Activity(BaseModel):
    """A single itinerary activity."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    category: str
    description: str = ""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    area: str = ""
    start_time: str = ""
    duration_min: int = Field(default=60, ge=0)
    cost_local: float = Field(default=0, ge=0)
    currency_local: str = "USD"
    cost_usd: float = Field(default=0, ge=0)
    cost_inr: float = Field(default=0, ge=0)
    tips: str = ""
    is_vegetarian_friendly: bool = True


class TimeSlot(BaseModel):
    """A chronological segment of a day."""

    slot_type: str
    activities: List[Activity] = Field(default_factory=list)
    transit_notes: str = ""


class DayPlan(BaseModel):
    """A complete plan for one day."""

    day_number: int = Field(ge=1)
    date: Optional[date_type] = None
    theme: str
    cluster_area: str = ""
    slots: List[TimeSlot] = Field(default_factory=list)
    day_total_usd: float = Field(default=0, ge=0)
    day_total_inr: float = Field(default=0, ge=0)
    day_total_local: float = Field(default=0, ge=0)
    transit_total_min: int = Field(default=0, ge=0)


class EmergencyInfo(BaseModel):
    """Emergency and practical local information."""

    police: str = ""
    ambulance: str = ""
    tourist_helpline: str = ""
    nearest_hospital_area: str = ""
    embassy_note: str = ""
    local_tips: List[str] = Field(default_factory=list)


class Itinerary(BaseModel):
    """The generated multi-day itinerary."""

    destination: str
    country: str = ""
    currency_local: str = "USD"
    days: List[DayPlan] = Field(default_factory=list)
    total_cost_usd: float = Field(default=0, ge=0)
    total_cost_inr: float = Field(default=0, ge=0)
    summary: str = ""
    emergency_info: EmergencyInfo = Field(default_factory=EmergencyInfo)


class SavedTrip(BaseModel):
    """Persisted trip record."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    preferences: TripPreferences
    itinerary: Itinerary
    notes: str = ""
