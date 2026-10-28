"""Tests for create-versus-update saved-trip semantics."""

from datetime import datetime, timezone

from core.config import SESSION_ITINERARY, SESSION_PREFERENCES, SESSION_SAVED_TRIP_ID
from core.demo_data import demo_itinerary
from core.models import TripPreferences
from core.storage import SQLiteTripRepository
from ui import tab_trips


def test_new_save_creates_unique_record_and_repeated_save_updates(monkeypatch, tmp_path):
    repository = SQLiteTripRepository(str(tmp_path / "trips.db"))
    state = {}
    monkeypatch.setattr(tab_trips.st, "session_state", state)
    preferences = TripPreferences(destination="Paris", days=2)
    itinerary = demo_itinerary("Paris", 2)

    first = tab_trips._save_current_trip(repository, "Paris escape", preferences, itinerary)
    first_created_at = first.created_at
    second = tab_trips._save_current_trip(
        repository, "Paris escape updated", preferences, itinerary
    )

    assert second.id == first.id
    assert second.title == "Paris escape updated"
    assert second.created_at == first_created_at
    assert len(repository.list_trips()) == 1


def test_loaded_trip_updates_without_changing_created_at(monkeypatch, tmp_path):
    repository = SQLiteTripRepository(str(tmp_path / "trips.db"))
    state = {SESSION_SAVED_TRIP_ID: "trip-1"}
    monkeypatch.setattr(tab_trips.st, "session_state", state)
    original = tab_trips._new_trip(
        "Original", TripPreferences(destination="Paris"), demo_itinerary("Paris", 2)
    ).model_copy(update={"id": "trip-1"})
    repository.save_trip(original)

    updated = tab_trips._save_current_trip(
        repository, "Renamed", original.preferences, original.itinerary
    )
    loaded = repository.get_trip("trip-1")

    assert loaded is not None
    assert updated.id == "trip-1"
    assert loaded.title == "Renamed"
    assert loaded.created_at == original.created_at
    assert loaded.updated_at >= original.updated_at
