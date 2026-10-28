"""Recommendation service tests."""

import json

import pytest

from core.config import SESSION_PREFERENCES
from core.demo_data import demo_destinations
from core.llm_client import DemoProvider
from core.models import TripPreferences
from core.recommender import RecommendationError, recommend_destinations


def test_demo_recommender_returns_exactly_three_and_respects_budget():
    results = recommend_destinations(
        TripPreferences(budget_level="Budget", vibes=["Beach"]),
        DemoProvider(),
    )
    assert len(results) == 3
    assert all(result.est_daily_cost_usd >= 0 for result in results)
    assert results[0].est_daily_cost_usd <= results[-1].est_daily_cost_usd


class InvalidProvider(DemoProvider):
    def generate(self, system_prompt, user_prompt, json_mode=True, temperature=0.7):
        return json.dumps({"recommendations": [{"city": "Only one"}]})


def test_invalid_provider_response_is_reported():
    with pytest.raises(RecommendationError, match="could not be validated"):
        recommend_destinations(TripPreferences(), InvalidProvider())
