"""Provider-isolated Gemini client for AI #1.

The provider knows nothing about BIS retrieval. Grounding policy belongs to
``prompts.py`` and answer generation belongs to ``answer_generator.py``.
"""

from __future__ import annotations

import logging
import time

from backend.app.core.config import settings
from backend.app.services.ai.prompts import GROUNDED_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Base error for provider failures."""


class LLMQuotaError(LLMError):
    """Raised when all configured Gemini keys are quota/rate limited."""


class LLMService:
    def __init__(self, api_keys=None, model=None):
        keys = list(api_keys if api_keys is not None else settings.LLM_API_KEYS)
        self.model = model or settings.LLM_MODEL
        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError as exc:
            raise LLMError("Gemini provider is not installed on the backend.") from exc

        # Deduplicate keys so the same credential is never retried as if it
        # were an independent quota pool. The SDK timeout is explicitly
        # bounded because grounded requests can legitimately take >5–10s.
        unique_keys = list(dict.fromkeys(k for k in keys if k))
        self._clients = []
        for key in unique_keys:
            try:
                self._clients.append(
                    genai.Client(
                        api_key=key,
                        http_options=genai_types.HttpOptions(
                            timeout=settings.LLM_REQUEST_TIMEOUT_MS,
                        ),
                    )
                )
            except TypeError:
                # Compatibility with older google-genai releases that do not
                # expose HttpOptions.timeout in the constructor.
                self._clients.append(genai.Client(api_key=key))

    @staticmethod
    def _is_quota_error(exc: Exception) -> bool:
        code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        return code == 429 or any(
            marker in str(exc).upper()
            for marker in ("RESOURCE_EXHAUSTED", "QUOTA", "RATE LIMIT")
        )

    def generate(self, prompt: str) -> str:
        return self.generate_with_system(prompt, GROUNDED_SYSTEM_PROMPT)

    def generate_with_system(self, prompt: str, system_instruction: str) -> str:
        """Generate text with an explicit system policy."""
        if not self._clients:
            raise LLMError("No LLM API key is configured on the backend.")

        try:
            from google.genai import errors as genai_errors
            from google.genai import types as genai_types
        except ImportError as exc:
            raise LLMError("Gemini provider is not installed on the backend.") from exc

        last_error = None
        calls_made = 0
        max_calls = max(1, settings.LLM_MAX_CALLS_PER_GENERATE)
        for index, client in enumerate(self._clients):
            if calls_made >= max_calls:
                break
            attempts = max(1, settings.LLM_TRANSIENT_RETRIES + 1)
            for attempt in range(attempts):
                if calls_made >= max_calls:
                    break
                calls_made += 1
                try:
                    response = client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=genai_types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            max_output_tokens=settings.MAX_OUTPUT_TOKENS,
                        ),
                    )
                    text = (response.text or "").strip()
                    if not text:
                        raise LLMError("The LLM returned an empty response.")
                    return text
                except genai_errors.APIError as exc:
                    last_error = exc
                    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
                    if self._is_quota_error(exc):
                        logger.warning(
                            "gemini_provider_quota key_index=%d status=%s", index + 1, status
                        )
                        break
                    # Retry common transient server-side failures once before
                    # moving to the next configured credential.
                    transient = status in {408, 425, 429, 500, 502, 503, 504}
                    logger.warning(
                        "gemini_provider_error key_index=%d attempt=%d status=%s type=%s transient=%s",
                        index + 1, attempt + 1, status, type(exc).__name__, transient,
                    )
                    if transient and attempt + 1 < attempts:
                        time.sleep(min(2 ** attempt, 2))
                        continue
                    break
                except LLMError as exc:
                    last_error = exc
                    logger.warning(
                        "gemini_client_error key_index=%d attempt=%d type=%s",
                        index + 1, attempt + 1, type(exc).__name__,
                    )
                    if attempt + 1 < attempts:
                        time.sleep(min(2 ** attempt, 2))
                        continue
                    break
                except Exception as exc:
                    last_error = exc
                    name = type(exc).__name__
                    message = str(exc).upper()
                    transient = any(
                        marker in name.upper() or marker in message
                        for marker in ("TIMEOUT", "CONNECT", "TEMPORARY", "503", "502", "504")
                    )
                    logger.warning(
                        "gemini_transport_error key_index=%d attempt=%d type=%s transient=%s",
                        index + 1, attempt + 1, name, transient,
                    )
                    if transient and attempt + 1 < attempts:
                        time.sleep(min(2 ** attempt, 2))
                        continue
                    break

            # Quota and other provider failures can try another configured key.
            # We deliberately do not claim that different keys have independent
            # project quotas; this is only a provider-failure fallback.
            if index < len(self._clients) - 1:
                continue

        if isinstance(last_error, Exception) and self._is_quota_error(last_error):
            raise LLMQuotaError("All configured LLM keys are quota limited.") from last_error
        raise LLMError("The LLM provider request failed.") from last_error


_default_service = None


def get_llm_service() -> LLMService:
    global _default_service
    if _default_service is None:
        _default_service = LLMService()
    return _default_service


def generate_reply(prompt: str) -> str:
    """Backward-compatible function used by older callers."""
    return get_llm_service().generate(prompt)
