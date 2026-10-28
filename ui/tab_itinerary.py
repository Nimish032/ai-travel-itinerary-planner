"""Day-by-day itinerary generation and visualization tab."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.budget import budget_cap_usd, cumulative_budget, over_budget_days
from core.config import SESSION_ITINERARY, SESSION_PREFERENCES
from core.itinerary import generate_itinerary
from core.models import TripPreferences


def _render_day(day, over_budget: bool) -> None:
    label = f"Day {day.day_number}: {day.theme}"
    with st.expander(label, expanded=day.day_number == 1):
        if over_budget:
            st.error("This day is above its approximate daily budget allocation.")
        st.caption(f"📍 {day.cluster_area} · 🚆 {day.transit_total_min} min transit")
        for slot in day.slots:
            icon = {
                "Morning Sightseeing": "🌅",
                "Lunch": "🍽️",
                "Afternoon Leisure": "🌴",
                "Evening Dining & Entertainment": "🌙",
            }.get(slot.slot_type, "•")
            st.markdown(f"**{icon} {slot.slot_type}**")
            for activity in slot.activities:
                st.write(
                    f"**{activity.name}** · {activity.duration_min} min · "
                    f"{activity.currency_local} {activity.cost_local:,.0f}"
                )
                if activity.tips:
                    st.caption(activity.tips)
        st.metric("Day total", f"${day.day_total_usd:,.2f}", f"₹{day.day_total_inr:,.0f}")


def render(provider=None) -> None:
    """Render itinerary generation and the resulting optimized plan."""

    preferences = st.session_state.get(SESSION_PREFERENCES, TripPreferences())
    st.subheader("🗺️ Day-by-day optimized itinerary")
    if not preferences.destination:
        st.info("Choose a destination in the sidebar or use the recommender first.")
    if provider is None:
        st.warning("Choose a provider in the sidebar.")
        return
    if st.button("🚀 Generate itinerary", type="primary", disabled=not preferences.destination):
        with st.status("Building your route...", expanded=True) as status:
            st.write("Collecting candidate places...")
            st.write("Clustering nearby experiences...")
            st.write("Calculating approximate costs...")
            try:
                st.session_state[SESSION_ITINERARY] = generate_itinerary(preferences, provider)
                status.update(label="Itinerary ready", state="complete")
            except Exception:
                status.update(label="Itinerary generation failed", state="error")
                st.error("We could not build the itinerary. Please try again.")
                return

    itinerary = st.session_state.get(SESSION_ITINERARY)
    if itinerary is None:
        st.markdown(
            '<div class="empty-state"><h3>Your optimized route starts here</h3>'
            "<p>Generate an itinerary to see clustered days, costs, and transit.</p></div>",
            unsafe_allow_html=True,
        )
        return
    cap = budget_cap_usd(preferences)
    metrics = st.columns(4)
    metrics[0].metric("Days", len(itinerary.days))
    metrics[1].metric("Total USD", f"${itinerary.total_cost_usd:,.2f}")
    metrics[2].metric("Total INR", f"₹{itinerary.total_cost_inr:,.0f}")
    metrics[3].metric("Avg daily spend", f"${itinerary.total_cost_usd / max(len(itinerary.days), 1):,.2f}")
    st.caption(f"Approximate trip budget cap: ${cap:,.0f}")
    tracker = cumulative_budget(itinerary)
    if tracker:
        st.line_chart(pd.DataFrame(tracker).set_index("day")[["cumulative_usd", "daily_usd"]])
    flagged = over_budget_days(itinerary, preferences)
    for day in itinerary.days:
        _render_day(day, day.day_number in flagged)
