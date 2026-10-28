"""Itinerary generation pipeline built on clustering and budget services."""

from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional, Sequence, Set

from core.budget import recalculate_day, recalculate_itinerary
from core.clustering import cluster_activities, order_clusters, transit_minutes
from core.demo_data import demo_itinerary
from core.json_utils import extract_json, validate_with_model
from core.llm_client import LLMProvider
from core.models import Activity, DayPlan, EmergencyInfo, Itinerary, TimeSlot, TripPreferences
from core.prompts import SYSTEM_PROMPT, candidate_pool_prompt, swap_prompt

SLOT_TYPES = [
    "Morning Sightseeing",
    "Lunch",
    "Afternoon Leisure",
    "Evening Dining & Entertainment",
]


def _demo_for_days(preferences: TripPreferences) -> Itinerary:
    itinerary = demo_itinerary(preferences.destination or "Paris", preferences.days)
    if len(itinerary.days) < preferences.days:
        base = itinerary.days[-1]
        for number in range(len(itinerary.days) + 1, preferences.days + 1):
            clone = base.model_copy(deep=True, update={
                "day_number": number,
                "date": (base.date + timedelta(days=number - base.day_number)) if base.date else None,
                "theme": f"{base.theme} · Day {number}",
            })
            itinerary.days.append(clone)
    itinerary.days = itinerary.days[:preferences.days]
    return recalculate_itinerary(itinerary)


def _activity_from_candidate(item: dict, currency: str = "EUR") -> Activity:
    return Activity(
        name=item["name"], category=item.get("category", "Sightseeing"),
        area=item.get("area", ""), lat=float(item["lat"]), lon=float(item["lon"]),
        duration_min=int(item.get("duration_min", 90)),
        cost_local=float(item.get("cost_local", 0)), currency_local=currency,
        is_vegetarian_friendly=item.get("meal_suitability", "yes") != "no",
    )


def _candidate_activities(provider: LLMProvider, preferences: TripPreferences) -> List[Activity]:
    response = provider.generate(
        SYSTEM_PROMPT,
        candidate_pool_prompt(
            preferences.destination or "Paris",
            preferences.days,
            preferences.model_dump(mode="json"),
        ),
    )
    payload = extract_json(response)
    items = payload.get("activities", []) if isinstance(payload, dict) else payload
    if not isinstance(items, list) or not items:
        raise ValueError("The candidate pool was empty.")
    return [_activity_from_candidate(item) for item in items]


def _day_from_cluster(
    cluster: Sequence[Activity], day_number: int, start: Optional[date]
) -> DayPlan:
    slots = [TimeSlot(slot_type=slot_type) for slot_type in SLOT_TYPES]
    for index, activity in enumerate(cluster):
        slots[min(index, 3)].activities.append(activity)
    hub = (cluster[0].lat, cluster[0].lon) if cluster else (0.0, 0.0)
    transit, _ = transit_minutes(cluster, hub)
    return DayPlan(
        day_number=day_number,
        date=start + timedelta(days=day_number - 1) if start else None,
        theme=f"Day {day_number}: {cluster[0].area or 'local highlights'}",
        cluster_area=cluster[0].area if cluster else "",
        slots=slots,
        transit_total_min=transit,
    )


def generate_itinerary(preferences: TripPreferences, provider: LLMProvider) -> Itinerary:
    """Generate a validated itinerary, using complete offline demo data when selected."""

    if provider.__class__.__name__ == "DemoProvider":
        return _demo_for_days(preferences)
    activities = _candidate_activities(provider, preferences)
    groups = order_clusters(
        cluster_activities(activities, preferences.days),
        (activities[0].lat, activities[0].lon),
    )
    days = [_day_from_cluster(group, index + 1, preferences.start_date)
            for index, group in enumerate(groups)]
    itinerary = Itinerary(
        destination=preferences.destination or "Unknown",
        days=days,
        summary="A geographically clustered itinerary generated from candidate activities.",
        emergency_info=EmergencyInfo(local_tips=["Confirm opening hours before leaving."]),
    )
    return recalculate_itinerary(itinerary)


def naive_route_distance(itinerary: Itinerary) -> float:
    """Compute a simple baseline by preserving slot/activity order."""

    total = 0.0
    for day in itinerary.days:
        points = [(activity.lat, activity.lon) for slot in day.slots for activity in slot.activities]
        from core.clustering import route_distance
        total += route_distance(points)
    return total


def _all_activities(itinerary: Itinerary) -> List[Activity]:
    return [
        activity
        for day in itinerary.days
        for slot in day.slots
        for activity in slot.activities
    ]


def _refresh_day(day: DayPlan) -> DayPlan:
    route = [activity for slot in day.slots for activity in slot.activities]
    if route:
        hub = (route[0].lat, route[0].lon)
        day.transit_total_min, _ = transit_minutes(route, hub)
    return day


def _recalculate_global_totals(itinerary: Itinerary) -> Itinerary:
    itinerary.total_cost_usd = sum(day.day_total_usd for day in itinerary.days)
    itinerary.total_cost_inr = sum(day.day_total_inr for day in itinerary.days)
    return itinerary


def _demo_swap(instruction: str, current: Activity) -> Activity:
    """Choose a deterministic nearby replacement for common demo intents."""

    lowered = instruction.lower()
    if "vegetarian" in lowered:
        name, category, cost, tips = "Seasonal vegetarian bistro", "Vegetarian Food", 14, "Ask for the chef's vegetable special."
    elif "cheap" in lowered:
        name, category, cost, tips = "Local bakery picnic", "Budget Food", 5, "Pick up a fresh pastry and fruit."
    elif "indoor" in lowered or "rain" in lowered:
        name, category, cost, tips = "Covered Passage discovery", "Indoor Culture", 8, "A comfortable rainy-day alternative."
    elif "outdoor" in lowered or "market" in lowered:
        name, category, cost, tips = "Marché neighborhood market", "Outdoor Market", 6, "Arrive before the lunch rush."
    elif "romantic" in lowered:
        name, category, cost, tips = "Seine sunset picnic", "Romantic Experience", 18, "Bring a light layer for the river breeze."
    else:
        name, category, cost, tips = "Local maker workshop", "Local Experience", 12, "Book ahead for a small-group session."
    return current.model_copy(
        deep=True,
        update={
            "id": current.id,
            "name": name,
            "category": category,
            "description": f"Demo replacement selected for: {instruction}",
            "cost_local": float(cost),
            "tips": tips,
        },
    )


def swap_activity(
    itinerary: Itinerary,
    day_number: int,
    slot_index: int,
    activity_index: int,
    instruction: str,
    preferences: TripPreferences,
    provider: LLMProvider,
) -> Itinerary:
    """Replace only one activity and recalculate the affected day and totals."""

    if not instruction.strip():
        raise ValueError("Describe the change you want to make.")
    day = next((item for item in itinerary.days if item.day_number == day_number), None)
    if day is None or slot_index < 0 or slot_index >= len(day.slots):
        raise ValueError("The selected itinerary day or slot does not exist.")
    slot = day.slots[slot_index]
    if activity_index < 0 or activity_index >= len(slot.activities):
        raise ValueError("The selected activity does not exist.")
    current = slot.activities[activity_index]
    if provider.__class__.__name__ == "DemoProvider":
        replacement = _demo_swap(instruction, current)
    else:
        context = {
            "day": day.model_dump(mode="json"),
            "neighbours": [
                activity.model_dump(mode="json")
                for candidate_slot in day.slots
                for activity in candidate_slot.activities
                if activity.id != current.id
            ],
        }
        response = provider.generate(
            SYSTEM_PROMPT,
            swap_prompt(context, instruction, preferences.model_dump(mode="json")),
        )
        replacement = validate_with_model(extract_json(response), Activity)
    slot.activities[activity_index] = replacement
    _refresh_day(day)
    recalculate_day(day)
    return _recalculate_global_totals(itinerary)


def regenerate_day(
    itinerary: Itinerary,
    day_number: int,
    preferences: TripPreferences,
    provider: LLMProvider,
) -> Itinerary:
    """Regenerate one day while excluding activity names used by other days."""

    target = next((day for day in itinerary.days if day.day_number == day_number), None)
    if target is None:
        raise ValueError("The selected itinerary day does not exist.")
    used: Set[str] = {
        activity.name
        for day in itinerary.days
        if day.day_number != day_number
        for slot in day.slots
        for activity in slot.activities
    }
    if provider.__class__.__name__ == "DemoProvider":
        base = demo_itinerary(preferences.destination or itinerary.destination, 2)
        source = base.days[(day_number - 1) % len(base.days)]
        replacement = source.model_copy(deep=True, update={"day_number": day_number})
        for slot in replacement.slots:
            slot.activities = [
                activity for activity in slot.activities if activity.name not in used
            ]
        replacement.slots = [
            slot for slot in replacement.slots if slot.activities
        ] or source.slots[:1]
    else:
        activities = _candidate_activities(provider, preferences)
        fresh = [activity for activity in activities if activity.name not in used]
        if not fresh:
            raise ValueError("No unused activities were returned for regeneration.")
        replacement = _day_from_cluster(fresh, day_number, preferences.start_date)
    itinerary.days = [
        replacement if day.day_number == day_number else day for day in itinerary.days
    ]
    recalculate_day(replacement)
    return _recalculate_global_totals(itinerary)
