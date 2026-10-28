"""Sidebar provider controls and validated trip preference form."""

from __future__ import annotations

import os
from datetime import date
from typing import Optional, Tuple

import streamlit as st
from dotenv import load_dotenv

from core.config import (
    BUDGET_LEVELS, DEFAULT_DAYS, DIETS, GEMINI_MODELS, GROQ_MODELS,
    GROQ_FALLBACK_MODEL,
    INTERESTS, PARTIES, PACES, PROVIDERS, SESSION_API_KEY, SESSION_MODEL,
    SESSION_PREFERENCES, SESSION_PROVIDER, VIBES,
)
from core.llm_client import DemoProvider, GeminiProvider, GroqProvider, LLMError, LLMProvider
from core.models import TripPreferences

load_dotenv()

def _secret_or_env(name: str) -> str:
    value = os.getenv(name, "")
    try:
        value = value or str(st.secrets.get(name, ""))
    except (FileNotFoundError, KeyError, RuntimeError):
        pass
    return value.strip()


def _provider_key(provider: str) -> str:
    return _secret_or_env("GEMINI_API_KEY" if provider == "Gemini" else "GROQ_API_KEY")


def get_provider(provider: str, model: str, api_key: str) -> LLMProvider:
    """Create a provider without exposing the secret."""

    if provider == "Gemini":
        return GeminiProvider(api_key, model)
    if provider == "Groq":
        fallback_model = os.getenv("GROQ_FALLBACK_MODEL", GROQ_FALLBACK_MODEL).strip()
        return GroqProvider(api_key, model, fallback_model=fallback_model)
    return DemoProvider()


def _date_inputs() -> Optional[date]:
    selected = st.date_input(
        "Travel start date (optional)",
        value=None,
        min_value=date.today(),
        help="Leave blank to keep dates flexible.",
    )
    return selected if isinstance(selected, date) else None


def _reset_preferences() -> None:
    """Reset preference data before the next widget tree is instantiated."""

    st.session_state[SESSION_PREFERENCES] = TripPreferences(days=DEFAULT_DAYS)
    for key in (
        "destination_input", "no_destination", "vibe_input", "days_input",
        "travelers_input", "interests_input",
    ):
        st.session_state.pop(key, None)


def render_sidebar() -> Tuple[LLMProvider, str]:
    """Render controls and store validated settings in session state."""

    with st.sidebar:
        st.header("✦ Trip preferences")
        provider_name = st.selectbox("AI provider", PROVIDERS, key="provider_select")
        default_key = _provider_key(provider_name) if provider_name != PROVIDERS[2] else ""
        entered_key = st.text_input(
            "API key", value=default_key, type="password",
            disabled=provider_name == PROVIDERS[2],
            help="Keys are kept in session state only and never logged.",
        )
        models = GEMINI_MODELS if provider_name == "Gemini" else GROQ_MODELS
        configured_model = os.getenv("GROQ_MODEL", "").strip()
        if provider_name == "Groq" and configured_model and configured_model not in models:
            models = [configured_model] + models
        model = st.selectbox(
            "Model", models, disabled=provider_name == PROVIDERS[2],
            key="model_select",
        )
        if provider_name == PROVIDERS[2]:
            st.info("Demo Mode is active. No API key is required.")
        if st.button("Test connection", use_container_width=True):
            try:
                test_provider = get_provider(provider_name, model, entered_key)
                test_provider.generate(
                    "Return a tiny JSON health response.",
                    '{"health_check": true}',
                    json_mode=True,
                    temperature=0,
                )
                st.success("Connection successful.")
            except LLMError as exc:
                st.error(str(exc))

        st.divider()
        st.caption("Your trip")
        destination = st.text_input("Destination (optional)", key="destination_input")
        no_destination = st.checkbox("I don't have a destination yet", key="no_destination")
        vibes = st.multiselect("Vibe", VIBES, key="vibe_input")
        days = int(st.number_input("Trip duration (days)", 1, 14, DEFAULT_DAYS, key="days_input"))
        start_date = _date_inputs()
        budget = st.selectbox("Budget level", BUDGET_LEVELS, key="budget_input")
        party = st.selectbox("Travel party", PARTIES, key="party_input")
        travelers = int(st.number_input("Number of travelers", 1, 50, 1, key="travelers_input"))
        pace = st.selectbox("Pace", PACES, index=1, key="pace_input")
        interests = st.multiselect("Interests", INTERESTS, key="interests_input")
        diet = st.selectbox("Dietary preference", DIETS, key="diet_input")
        currency = st.selectbox("Home currency", ["USD", "INR"], key="currency_input")

        if st.button("Save preferences", type="primary", use_container_width=True):
            if not no_destination and not destination.strip():
                st.error("Enter a destination or choose the destination recommender option.")
            elif start_date and start_date < date.today():
                st.error("Travel start date cannot be in the past.")
            else:
                st.session_state[SESSION_PREFERENCES] = TripPreferences(
                    destination=None if no_destination else destination.strip() or None,
                    vibes=vibes, days=days, start_date=start_date,
                    budget_level=budget, party=party, travelers=travelers,
                    pace=pace, interests=interests, diet=diet,
                    home_currency=currency,
                )
                st.session_state[SESSION_PROVIDER] = provider_name
                st.session_state[SESSION_MODEL] = model
                st.session_state[SESSION_API_KEY] = entered_key
                st.success("Preferences saved.")

        st.button(
            "Reset preferences",
            use_container_width=True,
            on_click=_reset_preferences,
        )

    stored_provider = st.session_state.get(SESSION_PROVIDER, provider_name)
    stored_model = st.session_state.get(SESSION_MODEL, model)
    stored_key = st.session_state.get(SESSION_API_KEY, entered_key)
    try:
        return get_provider(stored_provider, stored_model, stored_key), stored_provider
    except LLMError:
        st.warning("No valid API key is configured; Demo Mode is active.")
        return DemoProvider(), "Demo Mode (no key needed)"
