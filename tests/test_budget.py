"""Budget calculation tests."""

from core.budget import (
    activity_costs, budget_cap_usd, cumulative_budget, over_budget_days,
    recalculate_day, recalculate_itinerary, to_usd,
)
from core.models import Activity, DayPlan, Itinerary, TimeSlot, TripPreferences


def test_currency_conversion_and_activity_costs():
    assert to_usd(100, "USD") == 100
    assert to_usd(100, "INR") == 1.2
    activity = Activity(name="museum", category="art", lat=0, lon=0, cost_local=10, currency_local="EUR")
    assert activity_costs(activity)["usd"] == 10.8


def test_recalculate_totals_and_running_tracker():
    activity = Activity(name="museum", category="art", lat=0, lon=0, cost_local=10, currency_local="USD")
    itinerary = Itinerary(destination="Test", days=[
        DayPlan(day_number=1, theme="one", slots=[TimeSlot(slot_type="Morning", activities=[activity])]),
        DayPlan(day_number=2, theme="two", slots=[]),
    ])
    recalculate_itinerary(itinerary)
    assert itinerary.total_cost_usd == 10
    assert cumulative_budget(itinerary)[0]["cumulative_usd"] == 10


def test_budget_cap_and_flags():
    preferences = TripPreferences(days=2, travelers=1, budget_level="Budget")
    itinerary = Itinerary(destination="Test", days=[
        DayPlan(day_number=1, theme="one", day_total_usd=80),
        DayPlan(day_number=2, theme="two", day_total_usd=10),
    ])
    assert budget_cap_usd(preferences) == 150
    assert over_budget_days(itinerary, preferences) == [1]
