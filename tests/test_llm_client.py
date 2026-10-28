"""Tests for offline provider behavior."""

import json

import pytest

from core.demo_data import demo_destinations, demo_itinerary
from core.llm_client import DemoProvider, GeminiProvider, GroqProvider, LLMError


def test_demo_provider_returns_three_recommendations():
    data = json.loads(DemoProvider().generate("", "Recommend EXACTLY 3 destinations"))
    assert len(data["recommendations"]) == 3
    assert data["recommendations"][0]["city"] == "Paris"


def test_demo_data_has_six_destinations_and_two_days():
    assert len(demo_destinations()) >= 6
    itinerary = demo_itinerary("Paris", 3)
    assert len(itinerary.days) == 2
    assert all(day.slots for day in itinerary.days)


def test_provider_keys_are_required():
    with pytest.raises(LLMError, match="API key"):
        GeminiProvider("")
    with pytest.raises(LLMError, match="API key"):
        GroqProvider("")
