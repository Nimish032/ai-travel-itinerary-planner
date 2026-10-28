"""CRUD tests for the SQLite trip repository."""

from datetime import datetime, timezone

import pytest

from core.models import Itinerary, SavedTrip, TripPreferences
from core.storage import SQLiteTripRepository, TripRepositoryError


def make_trip(trip_id: str = "trip-1", title: str = "Paris escape") -> SavedTrip:
    now = datetime.now(timezone.utc)
    return SavedTrip(
        id=trip_id,
        title=title,
        created_at=now,
        updated_at=now,
        preferences=TripPreferences(destination="Paris", days=3),
        itinerary=Itinerary(destination="Paris", country="France", summary="A city break"),
        notes="Pack comfortable shoes",
    )


def test_schema_is_created_and_database_is_usable(tmp_path):
    repository = SQLiteTripRepository(str(tmp_path / "nested" / "trips.db"))
    assert repository.list_trips() == []


def test_save_and_get_round_trip_preserves_nested_models(tmp_path):
    repository = SQLiteTripRepository(str(tmp_path / "trips.db"))
    trip = make_trip()

    saved = repository.save_trip(trip)
    loaded = repository.get_trip(trip.id)

    assert saved == trip
    assert loaded == trip
    assert loaded is not None
    assert loaded.preferences.destination == "Paris"
    assert loaded.itinerary.country == "France"


def test_duplicate_id_is_rejected(tmp_path):
    repository = SQLiteTripRepository(str(tmp_path / "trips.db"))
    repository.save_trip(make_trip())

    with pytest.raises(TripRepositoryError, match="already exists"):
        repository.save_trip(make_trip())


def test_update_changes_content_and_timestamp(tmp_path):
    repository = SQLiteTripRepository(str(tmp_path / "trips.db"))
    repository.save_trip(make_trip())
    changed = make_trip(title="Updated Paris escape")
    changed.notes = "Updated notes"

    updated = repository.update_trip(changed)
    loaded = repository.get_trip("trip-1")

    assert updated.title == "Updated Paris escape"
    assert updated.updated_at >= changed.updated_at
    assert loaded is not None
    assert loaded.notes == "Updated notes"


def test_update_missing_trip_fails_explicitly(tmp_path):
    repository = SQLiteTripRepository(str(tmp_path / "trips.db"))

    with pytest.raises(TripRepositoryError, match="could not be found"):
        repository.update_trip(make_trip())


def test_list_supports_search_and_safe_sorting(tmp_path):
    repository = SQLiteTripRepository(str(tmp_path / "trips.db"))
    repository.save_trip(make_trip("paris", "Paris escape"))
    repository.save_trip(
        make_trip("goa", "Goa beach week").model_copy(
            update={"itinerary": Itinerary(destination="Goa")}
        )
    )

    assert [trip.id for trip in repository.list_trips(search="goa")] == ["goa"]
    assert [trip.id for trip in repository.list_trips(sort_by="title", descending=False)] == [
        "goa",
        "paris",
    ]
    with pytest.raises(ValueError, match="Unsupported"):
        repository.list_trips(sort_by="id")


def test_duplicate_creates_independent_new_record(tmp_path):
    repository = SQLiteTripRepository(str(tmp_path / "trips.db"))
    repository.save_trip(make_trip())

    duplicate = repository.duplicate_trip("trip-1")

    assert duplicate.id != "trip-1"
    assert duplicate.title == "Copy of Paris escape"
    assert repository.get_trip(duplicate.id) == duplicate
    assert repository.get_trip("trip-1") is not None


def test_delete_reports_existence(tmp_path):
    repository = SQLiteTripRepository(str(tmp_path / "trips.db"))
    repository.save_trip(make_trip())

    assert repository.delete_trip("trip-1") is True
    assert repository.get_trip("trip-1") is None
    assert repository.delete_trip("trip-1") is False
