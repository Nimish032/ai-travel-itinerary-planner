"""Tests for robust model-response parsing."""

import pytest

from core.json_utils import JSONExtractionError, extract_json, parse_and_validate
from core.models import DestinationRecommendation


def test_extracts_fenced_json():
    assert extract_json("Here you go:\n```json\n{\"ok\": true}\n```") == {"ok": True}


def test_extracts_json_embedded_in_prose():
    assert extract_json("Result: [1, {\"x\": 2}] Thanks") == [1, {"x": 2}]


def test_repairs_trailing_commas():
    assert extract_json('{"items": [1, 2,],}') == {"items": [1, 2]}


def test_handles_braces_inside_strings():
    assert extract_json('prefix {"text": "keep } this"} suffix') == {"text": "keep } this"}


def test_rejects_empty_or_invalid_text():
    with pytest.raises(JSONExtractionError):
        extract_json("")
    with pytest.raises(JSONExtractionError):
        extract_json("not JSON at all")


def test_validates_pydantic_model():
    payload = {
        "city": "Goa", "country": "India", "match_score": 90,
        "best_season": "Winter", "avg_temp_c": 28, "est_daily_cost_usd": 50,
        "highlight_tags": ["Beach"], "why_it_matches": "Warm and relaxed.",
        "lat": 15.3, "lon": 74.1,
    }
    result = parse_and_validate('prefix ' + str(payload).replace("'", '"'), DestinationRecommendation)
    assert result.city == "Goa"


def test_validation_error_is_explicit():
    with pytest.raises(JSONExtractionError, match="validation"):
        parse_and_validate('{"city": "Goa"}', DestinationRecommendation)
