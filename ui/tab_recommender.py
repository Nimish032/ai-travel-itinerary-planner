"""Smart destination recommendation tab."""

from __future__ import annotations

import streamlit as st

from core.config import SESSION_PREFERENCES, SESSION_RECOMMENDATIONS
from core.models import TripPreferences
from core.recommender import RecommendationError, recommend_destinations


def _select_recommendation(city: object) -> None:
    """Apply a selected recommendation before Streamlit creates widgets again."""

    if not isinstance(city, str) or not city.strip():
        return
    preferences = st.session_state.get(SESSION_PREFERENCES, TripPreferences())
    selected_city = city.strip()
    st.session_state[SESSION_PREFERENCES] = preferences.model_copy(
        update={"destination": selected_city}
    )
    st.session_state["destination_input"] = selected_city
    st.session_state["no_destination"] = False
    st.session_state["active_planning_message"] = (
        f"{selected_city} selected. Open the Itinerary tab to continue."
    )


def _render_card(index: int, recommendation) -> None:
    st.markdown(f"### {recommendation.city}, {recommendation.country}")
    st.progress(recommendation.match_score / 100, text=f"{recommendation.match_score}% match")
    st.caption(
        f"☀️ {recommendation.best_season} · {recommendation.avg_temp_c:.0f}°C · "
        f"Approx. ${recommendation.est_daily_cost_usd:,.0f}/day · "
        f"₹{recommendation.est_daily_cost_usd * 83:,.0f}/day"
    )
    st.markdown(" ".join(f"`{tag}`" for tag in recommendation.highlight_tags))
    st.write(recommendation.why_it_matches)
    city = getattr(recommendation, "city", "")
    st.button(
        f"Plan this trip: {city or 'destination'}",
        key=f"plan_{index}",
        disabled=not isinstance(city, str) or not city.strip(),
        on_click=_select_recommendation,
        args=(city,),
    )


def render(provider=None) -> None:
    """Render recommendations for the current preferences."""

    preferences = st.session_state.get(SESSION_PREFERENCES, TripPreferences())
    if preferences.destination:
        st.info(f"Planning for **{preferences.destination}**. Explore similar alternatives below.")
    else:
        st.subheader("Find your next somewhere")
    message = st.session_state.pop("active_planning_message", None)
    if message:
        st.success(message)

    if provider is None:
        st.warning("Choose a provider in the sidebar to get recommendations.")
        return
    if st.button("✨ Get 3 recommendations", type="primary"):
        with st.spinner("Matching destinations to your travel style..."):
            try:
                results = recommend_destinations(preferences, provider)
                st.session_state[SESSION_RECOMMENDATIONS] = results
            except RecommendationError as exc:
                st.error(str(exc))

    results = st.session_state.get(SESSION_RECOMMENDATIONS, [])
    if not results:
        st.markdown(
            '<div class="empty-state"><h3>Tell us what moves you</h3>'
            "<p>Save your preferences in the sidebar, then generate three "
            "personalized destinations.</p></div>",
            unsafe_allow_html=True,
        )
        return
    columns = st.columns(3)
    for index, recommendation in enumerate(results):
        with columns[index]:
            _render_card(index, recommendation)
