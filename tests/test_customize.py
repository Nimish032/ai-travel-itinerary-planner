"""Tests for targeted itinerary customization."""

from core.demo_data import demo_itinerary
from core.itinerary import regenerate_day, swap_activity
from core.llm_client import DemoProvider
from core.models import TripPreferences


def test_demo_swap_replaces_only_target_activity_and_recalculates_totals():
    itinerary = demo_itinerary("Paris", 2)
    original_other_day = itinerary.days[1].model_copy(deep=True)
    preferences = TripPreferences(destination="Paris", days=2)
    changed = swap_activity(
        itinerary, 1, 0, 0, "Cheaper option", preferences, DemoProvider()
    )
    assert changed.days[0].slots[0].activities[0].name == "Local bakery picnic"
    assert changed.days[1] == original_other_day
    assert changed.total_cost_usd != 0


def test_demo_swap_supports_instruction_keywords():
    itinerary = demo_itinerary("Paris", 2)
    changed = swap_activity(
        itinerary, 1, 1, 0, "Find vegetarian lunch spot",
        TripPreferences(destination="Paris"), DemoProvider()
    )
    activity = changed.days[0].slots[1].activities[0]
    assert activity.is_vegetarian_friendly
    assert "vegetarian" in activity.name.lower()


def test_regenerate_day_avoids_names_used_by_other_days():
    itinerary = demo_itinerary("Paris", 2)
    used_elsewhere = {
        activity.name
        for slot in itinerary.days[1].slots
        for activity in slot.activities
    }
    changed = regenerate_day(
        itinerary, 1, TripPreferences(destination="Paris", days=2), DemoProvider()
    )
    generated = {
        activity.name
        for slot in changed.days[0].slots
        for activity in slot.activities
    }
    assert generated
    assert not (generated & used_elsewhere)
