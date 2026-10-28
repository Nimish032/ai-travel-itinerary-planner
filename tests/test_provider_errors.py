"""Tests for safe provider error diagnostics."""

import logging

import pytest

from core.llm_client import LLMError, _RetryingProvider


class AlwaysFailProvider(_RetryingProvider):
    def __init__(self):
        super().__init__(max_retries=0)

    def _call(self, **kwargs):
        raise RuntimeError("simulated provider failure")


def test_provider_failure_has_user_facing_error_and_real_log(caplog):
    with caplog.at_level(logging.ERROR):
        with pytest.raises(LLMError, match="AI service could not complete"):
            AlwaysFailProvider().generate("system", "user")
    assert "simulated provider failure" in caplog.text
    assert "NoneType: None" not in caplog.text
