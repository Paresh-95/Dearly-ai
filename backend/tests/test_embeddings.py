import pytest

from app.core.config import get_settings
from app.services.providers.embeddings import FakeEmbeddingProvider, get_embedding_provider
from app.services.providers.errors import ProviderNotConfigured


def test_requires_configuration_by_default():
    get_embedding_provider.cache_clear()
    with pytest.raises(ProviderNotConfigured):
        get_embedding_provider()


class TestFakeEmbeddingProvider:
    def test_defaults_to_the_configured_dimension(self):
        provider = FakeEmbeddingProvider()
        [vector] = provider.embed(["hello"])
        assert len(vector) == get_settings().embedding_dim

    def test_is_deterministic_per_text(self):
        provider = FakeEmbeddingProvider()
        a1, a2, b = provider.embed(["same text", "same text", "different text"])
        assert a1 == a2
        assert a1 != b

    def test_batches_in_one_call_same_order(self):
        provider = FakeEmbeddingProvider()
        texts = ["one", "two", "three"]
        vectors = provider.embed(texts)
        assert len(vectors) == 3
        assert vectors == [provider.embed([t])[0] for t in texts]
