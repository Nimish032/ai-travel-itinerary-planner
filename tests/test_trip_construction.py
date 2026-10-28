"""Tests for canonical nested model validation when creating saved trips."""

from datetime import datetime, timezone

from core.demo_data import demo_itinerary
from core.models import Itinerary, SavedTrip, TripPreferences
from core.storage import SQLiteTripRepository
from ui.tab_trips import _new_trip


def test_new_trip_accepts_and_canonicalizes_nested_models():
    preferences = TripPreferences(destination="Paris", days=2)
    itinerary = demo_itinerary("Paris", 2)

    trip = _new_trip("Paris escape", preferences, itinerary)

    assert isinstance(trip, SavedTrip)
    assert type(trip.preferences) is TripPreferences
    assert type(trip.itinerary) is Itinerary
    assert trip.preferences.destination == "Paris"
    assert len(trip.itinerary.days) == 2


def test_new_trip_revalidates_serializable_nested_values():
    preferences = TripPreferences(destination="Paris", days=2)
    itinerary = demo_itinerary("Paris", 2)

    trip = _new_trip(
        "Paris escape",
        TripPreferences.model_validate(preferences.model_dump(mode="json")),
        Itinerary.model_validate(itinerary.model_dump(mode="json")),
    )

    assert trip.model_validate(trip.model_dump(mode="json")) == trip


def test_repository_saves_and_reloads_canonical_nested_models(tmp_path):
    now = datetime.now(timezone.utc)
    trip = SavedTrip(
        id="canonical-trip",
        title="Paris escape",
        created_at=now,
        updated_at=now,
        preferences=TripPreferences(destination="Paris", days=2),
        itinerary=demo_itinerary("Paris", 2),
    )
    repository = SQLiteTripRepository(str(tmp_path / "trips.db"))

    repository.save_trip(trip)
    loaded = repository.get_trip(trip.id)

    assert loaded is not None
    assert type(loaded.preferences) is TripPreferences
    assert type(loaded.itinerary) is Itinerary
    assert loaded.preferences == trip.preferences
    assert loaded.itinerary == trip.itinerary
