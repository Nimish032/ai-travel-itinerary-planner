"""Saved-trip management, portability, and PDF export."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import streamlit as st

from core.config import SESSION_ITINERARY, SESSION_PREFERENCES, SESSION_SAVED_TRIP_ID
from core.models import Itinerary, SavedTrip, TripPreferences
from core.pdf_export import generate_pdf
from core.storage import SQLiteTripRepository, TripRepositoryError

REPOSITORY_KEY = "trip_repository"


def _repository() -> SQLiteTripRepository:
    if REPOSITORY_KEY not in st.session_state:
        st.session_state[REPOSITORY_KEY] = SQLiteTripRepository()
    return st.session_state[REPOSITORY_KEY]


def _trip_json(trip: SavedTrip) -> bytes:
    return json.dumps(trip.model_dump(mode="json"), indent=2).encode("utf-8")


def _new_trip(
    title: str,
    preferences: TripPreferences,
    itinerary: Itinerary,
    notes: str = "",
) -> SavedTrip:
    """Build a trip using the canonical nested model classes.

    Re-validating through ``model_dump`` also handles stale Pydantic instances
    held in Streamlit session state after a source reload.
    """

    canonical_preferences = TripPreferences.model_validate(
        preferences.model_dump(mode="json")
    )
    canonical_itinerary = Itinerary.model_validate(
        itinerary.model_dump(mode="json")
    )
    now = datetime.now(timezone.utc)
    return SavedTrip(
        id=str(uuid4()), title=title, created_at=now, updated_at=now,
        preferences=canonical_preferences,
        itinerary=canonical_itinerary,
        notes=notes,
    )


def _save_current_trip(
    repository: SQLiteTripRepository,
    title: str,
    preferences: TripPreferences,
    itinerary: Itinerary,
) -> SavedTrip:
    """Create once, then update the currently loaded trip on later saves."""

    current_id = st.session_state.get(SESSION_SAVED_TRIP_ID)
    if current_id:
        existing = repository.get_trip(current_id)
        if existing is not None:
            return repository.update_trip(
                existing.model_copy(
                    update={
                        "title": title,
                        "preferences": preferences,
                        "itinerary": itinerary,
                    }
                )
            )
        st.session_state.pop(SESSION_SAVED_TRIP_ID, None)
    saved = repository.save_trip(_new_trip(title, preferences, itinerary))
    st.session_state[SESSION_SAVED_TRIP_ID] = saved.id
    return saved


def render() -> None:
    """Render saved trips and portability controls."""

    st.subheader("💼 Saved trips")
    repository = _repository()
    st.info("Streamlit Community Cloud storage is ephemeral. Download trips as JSON for portability.")
    current_preferences = st.session_state.get(SESSION_PREFERENCES)
    current_itinerary = st.session_state.get(SESSION_ITINERARY)
    if current_itinerary is not None and current_preferences is not None:
        title = st.text_input("Trip title", value=f"{current_itinerary.destination} adventure")
        if st.button("Save current itinerary", type="primary"):
            try:
                saved = _save_current_trip(
                    repository, title, current_preferences, current_itinerary
                )
                st.session_state[SESSION_SAVED_TRIP_ID] = saved.id
                st.success("Trip saved.")
            except TripRepositoryError as exc:
                st.error(str(exc))

    upload = st.file_uploader("Import trip from JSON", type=["json"])
    if upload is not None and st.button("Import uploaded trip"):
        try:
            trip = SavedTrip.model_validate(json.loads(upload.getvalue().decode("utf-8")))
            repository.save_trip(trip)
            st.session_state[SESSION_SAVED_TRIP_ID] = trip.id
            st.success("Trip imported.")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TripRepositoryError) as exc:
            st.error(f"Could not import trip JSON: {exc}")

    st.divider()
    search = st.text_input("Search saved trips")
    sort_label = st.selectbox("Sort by", ["Recently updated", "Title", "Destination", "Created"])
    sort_by = {"Recently updated": "updated_at", "Title": "title",
               "Destination": "destination", "Created": "created_at"}[sort_label]
    try:
        trips = repository.list_trips(search=search, sort_by=sort_by)
    except TripRepositoryError as exc:
        st.error(str(exc))
        return
    if not trips:
        st.markdown('<div class="empty-state"><h3>No saved trips yet</h3>'
                    "<p>Generate an itinerary, then save it here.</p></div>", unsafe_allow_html=True)
        return
    for trip in trips:
        with st.container(border=True):
            st.markdown(f"### {trip.title}")
            st.caption(f"{trip.itinerary.destination} · {trip.preferences.days} days · "
                       f"${trip.itinerary.total_cost_usd:,.2f} · "
                       f"Saved {trip.created_at.date().isoformat()}")
            if trip.notes:
                st.write(trip.notes)
            action_columns = st.columns(5)
            if action_columns[0].button("Load", key=f"load_{trip.id}"):
                st.session_state[SESSION_PREFERENCES] = trip.preferences
                st.session_state[SESSION_ITINERARY] = trip.itinerary
                st.session_state[SESSION_SAVED_TRIP_ID] = trip.id
                st.success("Trip loaded into the planner.")
            if action_columns[1].button("Duplicate", key=f"duplicate_{trip.id}"):
                try:
                    repository.duplicate_trip(trip.id)
                    st.rerun()
                except TripRepositoryError as exc:
                    st.error(str(exc))
            if action_columns[2].button("Delete", key=f"delete_{trip.id}"):
                repository.delete_trip(trip.id)
                st.rerun()
            new_title = action_columns[3].text_input("Rename", value=trip.title, key=f"title_{trip.id}")
            if action_columns[3].button("Apply", key=f"rename_{trip.id}") and new_title.strip():
                try:
                    repository.update_trip(trip.model_copy(update={"title": new_title.strip()}))
                    st.rerun()
                except TripRepositoryError as exc:
                    st.error(str(exc))
            notes = action_columns[4].text_input("Notes", value=trip.notes, key=f"notes_{trip.id}")
            if action_columns[4].button("Save notes", key=f"notes_save_{trip.id}"):
                try:
                    repository.update_trip(trip.model_copy(update={"notes": notes}))
                    st.rerun()
                except TripRepositoryError as exc:
                    st.error(str(exc))
            pdf = generate_pdf(trip)
            st.download_button(
                "Export PDF", pdf,
                file_name=f"Trip_{trip.itinerary.destination}_{trip.created_at.date().isoformat()}.pdf",
                mime="application/pdf", key=f"pdf_{trip.id}",
            )
            st.download_button(
                "Download trip as JSON", _trip_json(trip),
                file_name=f"Trip_{trip.itinerary.destination}.json",
                mime="application/json", key=f"json_{trip.id}",
            )
