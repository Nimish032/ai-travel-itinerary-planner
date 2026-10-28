"""Wanderlust visual theme."""

from __future__ import annotations

import streamlit as st


def inject_styles() -> None:
    """Inject the shared responsive application styling."""

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        :root { --teal: #0F766E; --coral: #F97316; --sand: #FEF3C7; --midnight: #0B1F33; }
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .hero { padding: 2rem 2.25rem; border-radius: 20px; color: white;
          background: linear-gradient(120deg, #0F766E 0%, #0EA5E9 55%, #F97316 100%);
          box-shadow: 0 12px 30px rgba(15,118,110,.18); margin-bottom: 1.5rem; }
        .hero h1 { margin: 0; font-size: clamp(2rem, 5vw, 3.2rem); }
        .hero p { margin: .5rem 0 0; font-size: 1.05rem; opacity: .94; }
        .mode-badge { display: inline-block; padding: .3rem .7rem; border-radius: 999px;
          background: rgba(255,255,255,.2); font-size: .8rem; font-weight: 700; }
        .empty-state { border: 1px dashed #94A3B8; border-radius: 16px; padding: 2rem;
          text-align: center; background: rgba(254,243,199,.35); }
        footer { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(mode: str) -> None:
    """Render the application header."""

    app_name = "Personalized Travel Itinerary Planner"
    tagline = "Plan less. Wander more."
    st.markdown(
        f"""
        <div class="hero">
          <span class="mode-badge">{mode}</span>
          <h1>✈ {app_name}</h1>
          <p>{tagline}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
