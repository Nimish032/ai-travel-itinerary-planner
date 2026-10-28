"""Vibe customization, targeted swaps, regeneration, and undo history."""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from core.config import SESSION_ITINERARY, SESSION_PREFERENCES
from core.itinerary import regenerate_day, swap_activity
from core.models import TripPreferences

HISTORY_KEY = "customization_history"
CHANGE_LOG_KEY = "customization_change_log"
QUICK_ACTIONS = [
    "Swap museum for outdoor market",
    "Find vegetarian lunch spot",
    "Make it more romantic",
    "Cheaper option",
    "Add a local experience",
    "Indoor alternative (rainy day)",
]


def _ensure_history() -> None:
    st.session_state.setdefault(HISTORY_KEY, [])
    st.session_state.setdefault(CHANGE_LOG_KEY, [])


def _activity_label(activity) -> str:
    return f"{activity.name} · {activity.category}"


def render(provider=None) -> None:
    """Render customization controls for the current itinerary."""

    _ensure_history()
    itinerary = st.session_state.get(SESSION_ITINERARY)
    preferences = st.session_state.get(SESSION_PREFERENCES, TripPreferences())
    st.subheader("✨ Vibe customization")
    if itinerary is None:
        st.markdown(
            '<div class="empty-state"><h3>Generate an itinerary first</h3>'
            "<p>Then you can swap one activity, regenerate a day, or undo a change.</p></div>",
            unsafe_allow_html=True,
        )
        return
    if provider is None:
        st.warning("Choose a provider in the sidebar.")
        return

    day_options = {f"Day {day.day_number}: {day.theme}": day for day in itinerary.days}
    selected_day_label = st.selectbox("Day to customize", list(day_options))
    selected_day = day_options[selected_day_label]
    slot_options = {
        f"{index + 1}. {slot.slot_type}": index
        for index, slot in enumerate(selected_day.slots)
        if slot.activities
    }
    if not slot_options:
        st.warning("This day has no activities to customize.")
        return
    selected_slot_label = st.selectbox("Slot", list(slot_options))
    slot_index = slot_options[selected_slot_label]
    slot = selected_day.slots[slot_index]
    activity_options = {_activity_label(activity): index for index, activity in enumerate(slot.activities)}
    selected_activity_label = st.selectbox("Activity", list(activity_options))
    activity_index = activity_options[selected_activity_label]
    current = slot.activities[activity_index]

    action = st.selectbox("Quick action", ["Custom instruction"] + QUICK_ACTIONS)
    instruction = st.text_area(
        "What should change?",
        value="" if action == "Custom instruction" else action,
        placeholder="Keep the replacement near the same neighborhood and respect my budget.",
    )
    if st.button("Apply change", type="primary"):
        before = current.model_copy(deep=True)
        try:
            st.session_state[HISTORY_KEY].append(itinerary.model_copy(deep=True))
            st.session_state[HISTORY_KEY] = st.session_state[HISTORY_KEY][-10:]
            updated = swap_activity(
                itinerary, selected_day.day_number, slot_index, activity_index,
                instruction, preferences, provider,
            )
            st.session_state[SESSION_ITINERARY] = updated
            st.session_state[CHANGE_LOG_KEY].append(
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} · "
                f"{before.name} → {updated.days[selected_day.day_number - 1].slots[slot_index].activities[activity_index].name}"
            )
            st.success("Activity updated; the rest of the itinerary stayed unchanged.")
            st.rerun()
        except (ValueError, RuntimeError) as exc:
            if st.session_state[HISTORY_KEY]:
                st.session_state[HISTORY_KEY].pop()
            st.error(str(exc))

    st.divider()
    st.markdown("#### Regenerate a complete day")
    if st.button("Regenerate selected day"):
        st.session_state[HISTORY_KEY].append(itinerary.model_copy(deep=True))
        st.session_state[HISTORY_KEY] = st.session_state[HISTORY_KEY][-10:]
        try:
            st.session_state[SESSION_ITINERARY] = regenerate_day(
                itinerary, selected_day.day_number, preferences, provider
            )
            st.session_state[CHANGE_LOG_KEY].append(
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} · "
                f"Regenerated day {selected_day.day_number}"
            )
            st.success("The selected day was regenerated.")
            st.rerun()
        except (ValueError, RuntimeError) as exc:
            st.session_state[HISTORY_KEY].pop()
            st.error(str(exc))

    if st.session_state[HISTORY_KEY] and st.button("Undo last change"):
        st.session_state[SESSION_ITINERARY] = st.session_state[HISTORY_KEY].pop()
        if st.session_state[CHANGE_LOG_KEY]:
            st.session_state[CHANGE_LOG_KEY].pop()
        st.success("Last customization undone.")
        st.rerun()

    st.markdown("#### Before / after preview")
    left, right = st.columns(2)
    with left:
        st.caption("Current selection")
        st.write(current.name)
        st.caption(f"{current.category} · {current.currency_local} {current.cost_local:,.0f}")
    with right:
        st.caption("Use Apply change to preview a replacement")
        st.write(current.name)
    if st.session_state[CHANGE_LOG_KEY]:
        st.markdown("#### Change log")
        for entry in reversed(st.session_state[CHANGE_LOG_KEY]):
            st.caption(entry)
