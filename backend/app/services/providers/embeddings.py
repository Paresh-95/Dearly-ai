"""Embeddings for approved memory chunks. Same honest-failure pattern as the other
providers (see docs/decisions/0003-provider-fallbacks.md): no key configured raises
`ProviderNotConfigured`, which `app.repositories.memory_chunks.reindex_memory` turns into
chunks left at `index_status='pending'` rather than fabricated vectors — a memory can still
be approved (it is a judgement about the content, not about search infrastructure), just not
searchable yet."""

from abc import ABC, abstractmethod
from functools import lru_cache

from openai import OpenAI

from app.core.config import get_settings
from app.services.providers.errors import ProviderNotConfigured


class EmbeddingProvider(ABC):
    model_name: str

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """One embedding per input text, same order. A single call for the whole batch —
        the brief's "use batching" for the handful of chunks one memory produces."""


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, *, api_key: str, base_url: str, model: str, dim: int) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model
        self._dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=self.model_name, input=texts, dimensions=self._dim
        )
        by_index = sorted(response.data, key=lambda d: d.index)
        return [d.embedding for d in by_index]


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic test double — never selected by configuration. Same text always
    produces the same vector, different text produces a different one, which is all the
    reindexing-idempotency tests need."""

    model_name = "fake-embedding-v1"

    def __init__(self, dim: int | None = None) -> None:
        # Defaults to the real configured dimension so it inserts cleanly into the
        # fixed-width pgvector column in tests, without hardcoding 1536 here too.
        self._dim = dim or get_settings().embedding_dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def _vector(self, text: str) -> list[float]:
        h = hash(text)
        return [((h >> (i * 4)) % 1000) / 1000 for i in range(self._dim)]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    s = get_settings()
    if not s.openai_api_key:
        raise ProviderNotConfigured(
            "No embedding provider is configured (MC_OPENAI_API_KEY is unset), "
            "so this memory cannot be indexed for search yet."
        )
    return OpenAIEmbeddingProvider(
        api_key=s.openai_api_key,
        base_url=s.openai_base_url,
        model=s.openai_embedding_model,
        dim=s.embedding_dim,
    )
