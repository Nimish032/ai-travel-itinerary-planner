"""Tests for recommendation-to-sidebar state handoff."""

from types import SimpleNamespace

from core.config import SESSION_PREFERENCES
from core.models import TripPreferences
from ui import tab_recommender


def test_selection_callback_updates_preference_and_widget_state(monkeypatch):
    state = {SESSION_PREFERENCES: TripPreferences(days=3)}
    monkeypatch.setattr(tab_recommender.st, "session_state", state)

    tab_recommender._select_recommendation("  Paris  ")

    assert state["destination_input"] == "Paris"
    assert state["no_destination"] is False
    assert state[SESSION_PREFERENCES].destination == "Paris"
    assert "Paris selected" in state["active_planning_message"]


def test_selection_callback_ignores_empty_city(monkeypatch):
    state = {SESSION_PREFERENCES: TripPreferences(days=3)}
    monkeypatch.setattr(tab_recommender.st, "session_state", state)

    tab_recommender._select_recommendation(SimpleNamespace(city=""))

    assert "destination_input" not in state
    assert state[SESSION_PREFERENCES].destination is None
