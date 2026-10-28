"""Destination recommendation orchestration and validation."""

from __future__ import annotations

import logging
from typing import List

from core.demo_data import demo_destinations
from core.json_utils import JSONExtractionError, extract_json, repair_prompt, validate_with_model
from core.llm_client import LLMError, LLMProvider
from core.models import DestinationRecommendation, TripPreferences
from core.prompts import SYSTEM_PROMPT, destination_prompt

LOGGER = logging.getLogger(__name__)


class RecommendationError(RuntimeError):
    """Raised when recommendations cannot be generated or validated."""


def _parse_recommendations(response: str) -> List[DestinationRecommendation]:
    payload = extract_json(response)
    if isinstance(payload, dict):
        payload = payload.get("recommendations")
    if not isinstance(payload, list) or len(payload) != 3:
        raise JSONExtractionError("The recommender must return exactly 3 destinations.")
    return [
        validate_with_model(item, DestinationRecommendation) for item in payload
    ]


def recommend_destinations(
    preferences: TripPreferences,
    provider: LLMProvider,
    force_regenerate: bool = False,
) -> List[DestinationRecommendation]:
    """Generate exactly three validated recommendations with two repair attempts."""

    del force_regenerate
    if provider.__class__.__name__ == "DemoProvider":
        return _filter_demo(preferences)

    prompt = destination_prompt(preferences.model_dump(mode="json"))
    last_error: Exception = RecommendationError("No response received.")
    for attempt in range(3):
        try:
            return _parse_recommendations(provider.generate(SYSTEM_PROMPT, prompt))
        except (JSONExtractionError, LLMError) as exc:
            last_error = exc
            if attempt < 2:
                prompt = repair_prompt(prompt, str(exc))
    LOGGER.exception("Recommendation generation failed")
    raise RecommendationError(
        "Recommendations could not be validated. Please try again or use Demo Mode."
    ) from last_error


def _filter_demo(preferences: TripPreferences) -> List[DestinationRecommendation]:
    records = demo_destinations()
    if preferences.vibes:
        wanted = {vibe.lower() for vibe in preferences.vibes}
        matching = [
            item for item in records
            if wanted.intersection({tag.lower() for tag in item.highlight_tags})
        ]
        if len(matching) >= 3:
            records = matching
    if preferences.budget_level == "Budget":
        records = sorted(records, key=lambda item: item.est_daily_cost_usd)
    elif preferences.budget_level == "Luxury":
        records = sorted(records, key=lambda item: item.est_daily_cost_usd, reverse=True)
    return records[:3]
