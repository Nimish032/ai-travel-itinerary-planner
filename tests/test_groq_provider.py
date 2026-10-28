"""Mocked Groq provider tests."""

from types import SimpleNamespace

import httpx
import pytest
import groq

from core.config import GROQ_DEFAULT_MODEL, GROQ_FALLBACK_MODEL
from core.llm_client import GroqProvider, LLMError


def _response(text="{}"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
    )


def test_configured_model_id_is_sent_to_groq(monkeypatch):
    calls = []

    class FakeCompletions:
        def create(self, **request):
            calls.append(request)
            return _response('{"ok": true}')

    class FakeGroq:
        def __init__(self, api_key):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(groq, "Groq", FakeGroq)
    provider = GroqProvider("test-key", model=GROQ_DEFAULT_MODEL)

    assert provider.generate("system", "user") == '{"ok": true}'
    assert calls[0]["model"] == GROQ_DEFAULT_MODEL
    assert calls[0]["temperature"] == 0.7
    assert calls[0]["response_format"] == {"type": "json_object"}


def test_model_not_found_uses_configured_groq_fallback(monkeypatch):
    calls = []
    response = httpx.Response(
        404, request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    )

    class FakeCompletions:
        def create(self, **request):
            calls.append(request["model"])
            if len(calls) == 1:
                raise groq.NotFoundError(
                    "model_not_found", response=response, body={"code": "model_not_found"}
                )
            return _response('{"fallback": true}')

    class FakeGroq:
        def __init__(self, api_key):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(groq, "Groq", FakeGroq)
    provider = GroqProvider("test-key", model=GROQ_DEFAULT_MODEL, fallback_model=GROQ_FALLBACK_MODEL)

    assert provider.generate("system", "user") == '{"fallback": true}'
    assert calls == [GROQ_DEFAULT_MODEL, GROQ_FALLBACK_MODEL]


def test_model_not_found_without_fallback_is_clear(monkeypatch):
    response = httpx.Response(
        404, request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    )

    class FakeCompletions:
        def create(self, **request):
            raise groq.NotFoundError(
                "model_not_found", response=response, body={"code": "model_not_found"}
            )

    class FakeGroq:
        def __init__(self, api_key):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(groq, "Groq", FakeGroq)
    provider = GroqProvider("test-key", model="account-specific-model", fallback_model=None)

    with pytest.raises(LLMError, match="unavailable to this account"):
        provider.generate("system", "user")
