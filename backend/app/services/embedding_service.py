"""Provider-neutral embedding service for Phase 10.

The service owns provider configuration and validation. Retrieval code depends on
this abstraction, so changing embedding vendors does not require changing the
database or ranking layer.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Protocol, Sequence

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    """Raised when an embedding cannot be produced."""


class EmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        ...


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str
    model: str
    dimensions: int
    max_input_chars: int
    batch_size: int
    retries: int


class GeminiEmbeddingProvider:
    """Gemini embedding provider using the current Google GenAI SDK."""

    def __init__(self, config: EmbeddingConfig):
        if not settings.EMBEDDING_API_KEY:
            raise EmbeddingError("Embedding provider is configured but no API key is set.")
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise EmbeddingError("google-genai is required for Gemini embeddings.") from exc

        self._types = types
        self._client = genai.Client(api_key=settings.EMBEDDING_API_KEY)
        self._config = config

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        # NOTE: gemini-embedding-2 / gemini-embedding-2-preview treat a list of
        # strings passed to `contents` as parts of a *single* document and
        # return one aggregated embedding, not one embedding per input (unlike
        # gemini-embedding-001). Sending this service's whole batch in one
        # call would silently collapse N inputs into 1 embedding and trip the
        # length-mismatch check below on every batch of more than one text.
        # Embedding one text per request is correct for every model version.
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        for attempt in range(self._config.retries + 1):
            try:
                result = self._client.models.embed_content(
                    model=self._config.model,
                    contents=[text],
                    config=self._types.EmbedContentConfig(
                        output_dimensionality=self._config.dimensions,
                    ),
                )
                embeddings = [
                    [float(v) for v in (item.values or [])]
                    for item in (result.embeddings or [])
                ]
                if len(embeddings) != 1:
                    raise EmbeddingError(
                        f"Provider returned {len(embeddings)} embeddings for 1 input."
                    )
                vector = embeddings[0]
                if len(vector) != self._config.dimensions:
                    raise EmbeddingError(
                        f"Embedding dimension {len(vector)} does not match "
                        f"configured dimension {self._config.dimensions}."
                    )
                return vector
            except EmbeddingError:
                raise
            except Exception as exc:
                if attempt >= self._config.retries:
                    raise EmbeddingError("Embedding provider request failed.") from exc
                time.sleep(min(2 ** attempt, 4))

        raise EmbeddingError("Embedding provider request failed.")


class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider | None = None):
        self.config = EmbeddingConfig(
            provider=settings.EMBEDDING_PROVIDER,
            model=settings.EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIMENSIONS,
            max_input_chars=settings.EMBEDDING_MAX_INPUT_CHARS,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            retries=settings.EMBEDDING_RETRIES,
        )
        self._provider = provider

    @property
    def available(self) -> bool:
        return self._provider is not None or (
            self.config.provider == "gemini" and bool(settings.EMBEDDING_API_KEY)
        )

    def _get_provider(self) -> EmbeddingProvider:
        if self._provider is None:
            if self.config.provider == "gemini":
                self._provider = GeminiEmbeddingProvider(self.config)
            else:
                raise EmbeddingError(
                    f"Unsupported embedding provider: {self.config.provider}"
                )
        return self._provider

    def _prepare(self, text: str) -> str:
        value = " ".join(str(text).split()).strip()
        if not value:
            raise EmbeddingError("Cannot embed empty text.")
        return value[: self.config.max_input_chars]

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        prepared = [self._prepare(t) for t in texts]
        if not prepared:
            return []

        provider = self._get_provider()
        output: list[list[float]] = []
        for start in range(0, len(prepared), self.config.batch_size):
            batch = prepared[start : start + self.config.batch_size]
            output.extend(provider.embed(batch))
        return output


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
