"""Approximate currency conversion and trip budget accounting."""

from __future__ import annotations

from typing import Dict, List

from core.config import EXCHANGE_RATES_TO_USD, USD_TO_INR
from core.models import Activity, DayPlan, Itinerary, TripPreferences

BUDGET_CAP_USD = {"Budget": 75.0, "Moderate": 160.0, "Luxury": 350.0}


def to_usd(amount: float, currency: str) -> float:
    rate = EXCHANGE_RATES_TO_USD.get(currency.upper())
    if rate is None:
        raise ValueError(f"Unsupported currency: {currency}")
    return amount * rate


def activity_costs(activity: Activity) -> Dict[str, float]:
    """Return approximate USD and INR costs, recalculated from local currency."""

    usd = to_usd(activity.cost_local, activity.currency_local)
    return {"local": activity.cost_local, "usd": usd, "inr": usd * USD_TO_INR}


def recalculate_day(day: DayPlan) -> DayPlan:
    costs = [activity_costs(activity) for slot in day.slots for activity in slot.activities]
    day.day_total_local = sum(item["local"] for item in costs)
    day.day_total_usd = sum(item["usd"] for item in costs)
    day.day_total_inr = sum(item["inr"] for item in costs)
    return day


def recalculate_itinerary(itinerary: Itinerary) -> Itinerary:
    for day in itinerary.days:
        recalculate_day(day)
    itinerary.total_cost_usd = sum(day.day_total_usd for day in itinerary.days)
    itinerary.total_cost_inr = sum(day.day_total_inr for day in itinerary.days)
    return itinerary


def budget_cap_usd(preferences: TripPreferences) -> float:
    return BUDGET_CAP_USD.get(preferences.budget_level, BUDGET_CAP_USD["Moderate"]) * preferences.days * preferences.travelers


def cumulative_budget(itinerary: Itinerary) -> List[Dict[str, float]]:
    running = 0.0
    output: List[Dict[str, float]] = []
    for day in itinerary.days:
        running += day.day_total_usd
        output.append({"day": float(day.day_number), "daily_usd": day.day_total_usd, "cumulative_usd": running})
    return output


def over_budget_days(itinerary: Itinerary, preferences: TripPreferences) -> List[int]:
    cap = budget_cap_usd(preferences)
    return [day.day_number for day in itinerary.days if day.day_total_usd > cap / max(preferences.days, 1)]
