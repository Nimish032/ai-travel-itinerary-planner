"""Persistence abstractions and the SQLite trip repository.

The repository stores the preference and itinerary models as JSON so the
application can migrate to a relational adapter without changing UI code.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from core.models import Itinerary, SavedTrip, TripPreferences

LOGGER = logging.getLogger(__name__)


class TripRepositoryError(RuntimeError):
    """Raised when trip persistence fails."""


class TripRepository(ABC):
    """Storage interface shared by local and future remote adapters."""

    @abstractmethod
    def save_trip(self, trip: SavedTrip) -> SavedTrip:
        """Create a trip and return the stored record."""
        raise NotImplementedError

    @abstractmethod
    def update_trip(self, trip: SavedTrip) -> SavedTrip:
        """Update an existing trip and return the stored record."""
        raise NotImplementedError

    @abstractmethod
    def get_trip(self, trip_id: str) -> Optional[SavedTrip]:
        """Return a trip by id, or None when it does not exist."""
        raise NotImplementedError

    @abstractmethod
    def list_trips(
        self,
        search: str = "",
        sort_by: str = "updated_at",
        descending: bool = True,
    ) -> List[SavedTrip]:
        """Return trips matching an optional title/destination search."""
        raise NotImplementedError

    @abstractmethod
    def delete_trip(self, trip_id: str) -> bool:
        """Delete a trip and report whether a row was removed."""
        raise NotImplementedError

    @abstractmethod
    def duplicate_trip(self, trip_id: str, title: Optional[str] = None) -> SavedTrip:
        """Copy a trip under a new id."""
        raise NotImplementedError


class SQLiteTripRepository(TripRepository):
    """SQLite-backed implementation with parameterized queries and transactions."""

    _SORT_COLUMNS = {"title", "destination", "created_at", "updated_at"}

    def __init__(self, db_path: str = "data/trips.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize_schema(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trips (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        destination TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        preferences_json TEXT NOT NULL,
                        itinerary_json TEXT NOT NULL,
                        notes TEXT NOT NULL DEFAULT ''
                    )
                    """
                )
        except sqlite3.Error as exc:
            LOGGER.exception("Could not initialize trip database")
            raise TripRepositoryError("Could not initialize trip storage.") from exc

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _serialize(trip: SavedTrip) -> tuple:
        return (
            trip.id,
            trip.title,
            trip.itinerary.destination,
            trip.created_at.isoformat(),
            trip.updated_at.isoformat(),
            json.dumps(trip.preferences.model_dump(mode="json")),
            json.dumps(trip.itinerary.model_dump(mode="json")),
            trip.notes,
        )

    @staticmethod
    def _deserialize(row: sqlite3.Row) -> SavedTrip:
        try:
            return SavedTrip(
                id=row["id"],
                title=row["title"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                preferences=TripPreferences.model_validate(
                    json.loads(row["preferences_json"])
                ),
                itinerary=Itinerary.model_validate(json.loads(row["itinerary_json"])),
                notes=row["notes"] or "",
            )
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            LOGGER.exception("Stored trip data is invalid")
            raise TripRepositoryError("Stored trip data could not be read.") from exc

    def save_trip(self, trip: SavedTrip) -> SavedTrip:
        """Insert a trip; duplicate ids are rejected explicitly."""

        # Normalize nested values at the persistence boundary so callers
        # holding stale/reloaded Pydantic instances still get canonical data.
        trip = SavedTrip.model_validate(trip.model_dump(mode="json"))
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO trips (
                        id, title, destination, created_at, updated_at,
                        preferences_json, itinerary_json, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._serialize(trip),
                )
            return trip
        except sqlite3.IntegrityError as exc:
            LOGGER.warning("Trip id already exists: %s", trip.id)
            raise TripRepositoryError("A trip with this id already exists.") from exc
        except sqlite3.Error as exc:
            LOGGER.exception("Could not save trip")
            raise TripRepositoryError("Could not save the trip.") from exc

    def update_trip(self, trip: SavedTrip) -> SavedTrip:
        """Update all mutable fields while preserving the original created time."""

        trip = SavedTrip.model_validate(trip.model_dump(mode="json"))
        try:
            with self._connect() as connection:
                existing_row = connection.execute(
                    "SELECT created_at FROM trips WHERE id = ?", (trip.id,)
                ).fetchone()
                if existing_row is None:
                    raise TripRepositoryError("The trip could not be found.")
                existing_created_at = datetime.fromisoformat(existing_row["created_at"])
                updated_trip = trip.model_copy(
                    update={
                        "created_at": existing_created_at,
                        "updated_at": self._now(),
                    }
                )
                cursor = connection.execute(
                    """
                    UPDATE trips
                    SET title = ?, destination = ?, updated_at = ?,
                        preferences_json = ?, itinerary_json = ?, notes = ?
                    WHERE id = ?
                    """,
                    (
                        updated_trip.title,
                        updated_trip.itinerary.destination,
                        updated_trip.updated_at.isoformat(),
                        json.dumps(updated_trip.preferences.model_dump(mode="json")),
                        json.dumps(updated_trip.itinerary.model_dump(mode="json")),
                        updated_trip.notes,
                        updated_trip.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise TripRepositoryError("The trip could not be found.")
            return updated_trip
        except TripRepositoryError:
            raise
        except sqlite3.Error as exc:
            LOGGER.exception("Could not update trip")
            raise TripRepositoryError("Could not update the trip.") from exc

    def get_trip(self, trip_id: str) -> Optional[SavedTrip]:
        """Fetch one trip without exposing SQLite rows to callers."""

        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM trips WHERE id = ?", (trip_id,)
                ).fetchone()
            return self._deserialize(row) if row is not None else None
        except sqlite3.Error as exc:
            LOGGER.exception("Could not read trip")
            raise TripRepositoryError("Could not load the trip.") from exc

    def list_trips(
        self,
        search: str = "",
        sort_by: str = "updated_at",
        descending: bool = True,
    ) -> List[SavedTrip]:
        """List trips with safe allow-listed sorting and case-insensitive search."""

        if sort_by not in self._SORT_COLUMNS:
            raise ValueError("Unsupported trip sort field.")
        direction = "DESC" if descending else "ASC"
        query = (
            "SELECT * FROM trips "
            "WHERE title LIKE ? COLLATE NOCASE OR destination LIKE ? COLLATE NOCASE "
            f"ORDER BY {sort_by} {direction}"
        )
        term = f"%{search}%"
        try:
            with self._connect() as connection:
                rows = connection.execute(query, (term, term)).fetchall()
            return [self._deserialize(row) for row in rows]
        except sqlite3.Error as exc:
            LOGGER.exception("Could not list trips")
            raise TripRepositoryError("Could not list saved trips.") from exc

    def delete_trip(self, trip_id: str) -> bool:
        """Delete one trip and return whether it existed."""

        try:
            with self._connect() as connection:
                cursor = connection.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
            return cursor.rowcount > 0
        except sqlite3.Error as exc:
            LOGGER.exception("Could not delete trip")
            raise TripRepositoryError("Could not delete the trip.") from exc

    def duplicate_trip(self, trip_id: str, title: Optional[str] = None) -> SavedTrip:
        """Create a new record with copied content and fresh timestamps."""

        original = self.get_trip(trip_id)
        if original is None:
            raise TripRepositoryError("The trip to duplicate could not be found.")
        now = self._now()
        duplicate = original.model_copy(
            deep=True,
            update={
                "id": str(uuid4()),
                "title": title or f"Copy of {original.title}",
                "created_at": now,
                "updated_at": now,
            },
        )
        return self.save_trip(duplicate)


class SupabaseTripRepository(TripRepository):
    """Future adapter placeholder.

    A Supabase implementation should map this interface to relational
    ``users``, ``trips``, ``days``, and ``activities`` tables and keep model
    validation at this boundary. The local SQLite adapter remains the default
    so the app works offline and on Streamlit Community Cloud.
    """

    def __init__(self) -> None:
        raise NotImplementedError(
            "Supabase persistence is reserved for the future remote adapter."
        )

    def save_trip(self, trip: SavedTrip) -> SavedTrip:
        raise NotImplementedError

    def update_trip(self, trip: SavedTrip) -> SavedTrip:
        raise NotImplementedError

    def get_trip(self, trip_id: str) -> Optional[SavedTrip]:
        raise NotImplementedError

    def list_trips(
        self,
        search: str = "",
        sort_by: str = "updated_at",
        descending: bool = True,
    ) -> List[SavedTrip]:
        raise NotImplementedError

    def delete_trip(self, trip_id: str) -> bool:
        raise NotImplementedError

    def duplicate_trip(self, trip_id: str, title: Optional[str] = None) -> SavedTrip:
        raise NotImplementedError
