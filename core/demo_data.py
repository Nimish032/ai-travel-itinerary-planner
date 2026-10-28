"""Rich deterministic data for a complete offline demo experience."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from core.models import (
    Activity,
    DayPlan,
    DestinationRecommendation,
    EmergencyInfo,
    Itinerary,
    TimeSlot,
)


def demo_destinations() -> List[DestinationRecommendation]:
    """Return six real destinations covering the principal travel vibes."""

    records = [
        ("Paris", "France", 92, "April to June", 16, 120, ["Art", "Cafes"], "A culture-rich city break."),
        ("Goa", "India", 89, "November to February", 28, 55, ["Beach", "Street Food"], "Sunny beaches and relaxed local experiences."),
        ("Tokyo", "Japan", 87, "March to May", 17, 105, ["Food", "Urban"], "High-energy neighborhoods with exceptional food."),
        ("Jaipur", "India", 86, "October to March", 24, 48, ["Heritage", "Crafts"], "Colorful forts, markets, and living history."),
        ("Bali", "Indonesia", 90, "April to October", 27, 62, ["Wellness", "Nature"], "A restorative mix of temples, rice terraces, and coast."),
        ("Bangkok", "Thailand", 85, "November to February", 29, 50, ["Night Markets", "Food"], "A lively and affordable urban adventure."),
    ]
    coordinates = {
        "Paris": (48.8566, 2.3522), "Goa": (15.2993, 74.1240),
        "Tokyo": (35.6762, 139.6503), "Jaipur": (26.9124, 75.7873),
        "Bali": (-8.4095, 115.1889), "Bangkok": (13.7563, 100.5018),
    }
    return [
        DestinationRecommendation(
            city=city, country=country, match_score=score, best_season=season,
            avg_temp_c=temp, est_daily_cost_usd=cost, highlight_tags=tags,
            why_it_matches=why, lat=coordinates[city][0], lon=coordinates[city][1],
        )
        for city, country, score, season, temp, cost, tags, why in records
    ]


def _activity(
    name: str, category: str, lat: float, lon: float, area: str,
    start: str, cost: float, tips: str, duration: int = 90,
) -> Activity:
    return Activity(
        name=name, category=category, description=f"Demo experience: {name}.",
        lat=lat, lon=lon, area=area, start_time=start, duration_min=duration,
        cost_local=cost, currency_local="EUR", cost_usd=cost * 1.08,
        cost_inr=cost * 1.08 * 83, tips=tips,
    )


def demo_itinerary(destination: str = "Paris", days: int = 3) -> Itinerary:
    """Return a complete deterministic itinerary, with two detailed days."""

    city = destination.strip() or "Paris"
    paris_days = [
        DayPlan(
            day_number=1, date=date(2026, 4, 10), theme="Classic Paris icons",
            cluster_area="Île de la Cité & Louvre", slots=[
                TimeSlot(slot_type="Morning Sightseeing", activities=[
                    _activity("Louvre Museum", "History & Art", 48.8606, 2.3376, "Louvre", "09:00", 22, "Book the first entry slot.")
                ]),
                TimeSlot(slot_type="Lunch", activities=[
                    _activity("Le Marais market lunch", "Food", 48.8566, 2.3622, "Le Marais", "12:30", 16, "Ask for a seasonal special.")
                ]),
                TimeSlot(slot_type="Afternoon Leisure", activities=[
                    _activity("Seine riverside walk", "Nature", 48.8584, 2.2945, "Seine", "14:30", 0, "Wear comfortable shoes.")
                ]),
                TimeSlot(slot_type="Evening Dining & Entertainment", activities=[
                    _activity("Latin Quarter dinner", "Food", 48.8499, 2.3470, "Latin Quarter", "19:00", 28, "Reserve a small table.")
                ]),
            ], day_total_usd=71.28, day_total_inr=5916.24, day_total_local=66, transit_total_min=44,
        ),
        DayPlan(
            day_number=2, date=date(2026, 4, 11), theme="Montmartre creative morning",
            cluster_area="Montmartre", slots=[
                TimeSlot(slot_type="Morning Sightseeing", activities=[
                    _activity("Sacré-Cœur Basilica", "Culture", 48.8867, 2.3431, "Montmartre", "09:30", 0, "Arrive early for quiet views.")
                ]),
                TimeSlot(slot_type="Lunch", activities=[
                    _activity("Montmartre crêperie", "Food", 48.8841, 2.3402, "Montmartre", "12:30", 15, "Try a buckwheat galette.")
                ]),
                TimeSlot(slot_type="Afternoon Leisure", activities=[
                    _activity("Artists' Square", "Art", 48.8864, 2.3405, "Montmartre", "14:00", 0, "Support local artists.")
                ]),
                TimeSlot(slot_type="Evening Dining & Entertainment", activities=[
                    _activity("Canal Saint-Martin dinner", "Food", 48.8720, 2.3656, "Canal Saint-Martin", "19:30", 25, "Explore the canal after dinner.")
                ]),
            ], day_total_usd=43.2, day_total_inr=3585.6, day_total_local=40, transit_total_min=38,
        ),
    ]
    if city.lower() != "paris":
        recommendations = demo_destinations()
        match = next((item for item in recommendations if item.city.lower() == city.lower()), recommendations[0])
        return Itinerary(
            destination=match.city, country=match.country, currency_local="USD",
            days=paris_days[: max(1, min(days, len(paris_days)))],
            total_cost_usd=sum(day.day_total_usd for day in paris_days[:2]),
            total_cost_inr=sum(day.day_total_inr for day in paris_days[:2]),
            summary=f"Offline demo itinerary for {match.city}.",
            emergency_info=EmergencyInfo(police="112", ambulance="112", tourist_helpline="1000"),
        )
    selected_days = paris_days[: max(1, min(days, len(paris_days)))]
    return Itinerary(
        destination="Paris", country="France", currency_local="EUR",
        days=selected_days,
        total_cost_usd=sum(day.day_total_usd for day in selected_days),
        total_cost_inr=sum(day.day_total_inr for day in selected_days),
        summary="A balanced offline demo of Parisian art, food, and neighborhoods.",
        emergency_info=EmergencyInfo(
            police="17", ambulance="15", tourist_helpline="34 24",
            nearest_hospital_area="Central Paris", embassy_note="Keep a copy of your passport.",
            local_tips=["Validate metro tickets before boarding.", "Carry a refillable water bottle."],
        ),
    )


def demo_response(user_prompt: str) -> Any:
    """Choose deterministic JSON-shaped output based on prompt task keywords."""

    lowered = user_prompt.lower()
    if "recommend exactly 3" in lowered or "recommendations" in lowered:
        return {"recommendations": [item.model_dump(mode="json") for item in demo_destinations()[:3]]}
    if "candidate pool" in lowered or "activities array" in lowered:
        return {"activities": [
            {"name": "Louvre Museum", "category": "Art", "area": "Louvre", "lat": 48.8606, "lon": 2.3376,
             "cost_local": 22, "duration_min": 120, "indoor_or_outdoor": "indoor", "meal_suitability": "no"},
            {"name": "Seine Walk", "category": "Nature", "area": "Seine", "lat": 48.8584, "lon": 2.2945,
             "cost_local": 0, "duration_min": 90, "indoor_or_outdoor": "outdoor", "meal_suitability": "no"},
        ]}
    if "one activity json object" in lowered:
        return _activity("Covered Passage discovery", "Local Experience", 48.8646, 2.3420, "Louvre", "15:00", 8, "Look for independent bookshops.").model_dump(mode="json")
    itinerary = demo_itinerary()
    return itinerary.model_dump(mode="json")
