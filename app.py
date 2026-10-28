"""Streamlit entry point for the Personalized Travel Itinerary Planner."""

from __future__ import annotations

import streamlit as st

from core.config import (
    DEFAULT_DAYS,
    SESSION_INITIALIZED,
    SESSION_PREFERENCES,
)
from core.models import TripPreferences
from ui import styles
from ui import sidebar
from ui import tab_customize, tab_itinerary, tab_recommender, tab_trips


def init_state() -> None:
    """Initialize all Phase 1 session state in one place."""

    if st.session_state.get(SESSION_INITIALIZED):
        return
    st.session_state[SESSION_PREFERENCES] = TripPreferences(days=DEFAULT_DAYS)
    st.session_state[SESSION_INITIALIZED] = True


def main() -> None:
    """Configure and render the application."""

    st.set_page_config(
        page_title="Personalized Travel Itinerary Planner",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()
    styles.inject_styles()
    provider, provider_name = sidebar.render_sidebar()
    styles.render_hero(provider_name)

    tabs = st.tabs(
        ["🌍 Recommend", "🗺️ Itinerary", "✨ Customize", "💼 Saved trips"]
    )
    with tabs[0]:
        tab_recommender.render(provider)
    with tabs[1]:
        tab_itinerary.render(provider)
    with tabs[2]:
        tab_customize.render(provider)
    with tabs[3]:
        tab_trips.render()

    st.caption("Personalized Travel Itinerary Planner · Skill Wallet Capstone Project 4")


if __name__ == "__main__":
    main()
