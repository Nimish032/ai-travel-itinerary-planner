"""LLM provider abstraction with lazy SDK loading and demo mode."""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from core.config import GROQ_DEFAULT_MODEL, GROQ_FALLBACK_MODEL
from core.demo_data import demo_response

LOGGER = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """User-facing provider error with a safe message."""


class LLMProvider(ABC):
    """Common interface for Gemini, Groq, and demo providers."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True,
        temperature: float = 0.7,
    ) -> str:
        raise NotImplementedError


class DemoProvider(LLMProvider):
    """Deterministic offline provider used by default and in tests."""

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True,
        temperature: float = 0.7,
    ) -> str:
        del system_prompt, temperature
        response = demo_response(user_prompt)
        if json_mode:
            return json.dumps(response)
        return json.dumps(response)


class _RetryingProvider(LLMProvider):
    def __init__(self, max_retries: int = 2) -> None:
        self.max_retries = max_retries

    def _call(self, **kwargs: Any) -> str:
        raise NotImplementedError

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True,
        temperature: float = 0.7,
    ) -> str:
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._call(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    json_mode=json_mode,
                    temperature=temperature,
                )
                if not response or not response.strip():
                    raise LLMError("The model returned an empty response.")
                return response
            except LLMError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
        if last_error is not None:
            LOGGER.error(
                "LLM provider request failed after %d attempt(s): %s",
                self.max_retries + 1,
                last_error,
                exc_info=last_error,
            )
        else:
            LOGGER.error("LLM provider request failed without an exception.")
        raise LLMError(
            "The AI service could not complete the request. Check your key, "
            "model, connection, or quota and try again."
        ) from last_error


class GeminiProvider(_RetryingProvider):
    """Google Gemini provider using the current generativeai SDK interface."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        super().__init__()
        if not api_key.strip():
            raise LLMError("A Gemini API key is required.")
        self.api_key = api_key
        self.model_name = model

    def _call(self, **kwargs: Any) -> str:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise LLMError("The Gemini SDK is not installed.") from exc
        genai.configure(api_key=self.api_key)
        generation_config: Dict[str, Any] = {
            "temperature": kwargs["temperature"],
        }
        if kwargs["json_mode"]:
            generation_config["response_mime_type"] = "application/json"
        model = genai.GenerativeModel(
            self.model_name,
            system_instruction=kwargs["system_prompt"],
        )
        response = model.generate_content(
            kwargs["user_prompt"], generation_config=generation_config
        )
        return getattr(response, "text", "") or ""


class GroqProvider(_RetryingProvider):
    """Groq provider with JSON response formatting when requested."""

    def __init__(
        self,
        api_key: str,
        model: str = GROQ_DEFAULT_MODEL,
        fallback_model: Optional[str] = GROQ_FALLBACK_MODEL,
    ) -> None:
        super().__init__()
        if not api_key.strip():
            raise LLMError("A Groq API key is required.")
        self.api_key = api_key
        self.model_name = model
        self.fallback_model = fallback_model if fallback_model != model else None

    def _call(self, **kwargs: Any) -> str:
        try:
            from groq import Groq, NotFoundError
        except ImportError as exc:
            raise LLMError("The Groq SDK is not installed.") from exc
        client = Groq(api_key=self.api_key)
        try:
            return self._complete(client, self.model_name, kwargs)
        except NotFoundError as exc:
            if not self.fallback_model:
                raise LLMError(
                    f"Groq model '{self.model_name}' is unavailable to this account. "
                    "Set GROQ_MODEL to a model enabled for your account."
                ) from exc
            LOGGER.warning(
                "Groq model '%s' was unavailable; using configured fallback '%s'.",
                self.model_name,
                self.fallback_model,
            )
            try:
                return self._complete(client, self.fallback_model, kwargs)
            except NotFoundError as fallback_error:
                raise LLMError(
                    f"Groq models '{self.model_name}' and fallback "
                    f"'{self.fallback_model}' are unavailable to this account. "
                    "Set GROQ_MODEL and GROQ_FALLBACK_MODEL to enabled models."
                ) from fallback_error

    @staticmethod
    def _complete(client: Any, model: str, kwargs: Dict[str, Any]) -> str:
        request: Dict[str, Any] = {
            "model": model,
            "temperature": kwargs["temperature"],
            "messages": [
                {"role": "system", "content": kwargs["system_prompt"]},
                {"role": "user", "content": kwargs["user_prompt"]},
            ],
        }
        if kwargs["json_mode"]:
            request["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**request)
        return response.choices[0].message.content or ""
