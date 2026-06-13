"""Tests for the pluggable embedding provider adapters."""

import numpy as np

from src.providers.embedding_adapters import (
    FastEmbedEmbeddingProvider,
    HostedEmbeddingProvider,
    KeywordEmbeddingProvider,
    wrap_embedding_client,
)


class _FakeClient:
    def __init__(self, url, model="fake-model", dim=4):
        self.url = url
        self.model = model
        self._dim = dim

    def encode(self, texts, normalize_embeddings=True):
        return np.ones((len(texts), self._dim), dtype="float32")

    def get_sentence_embedding_dimension(self):
        return self._dim


def test_hosted_adapter_delegates():
    client = _FakeClient(url="http://x/v1/embeddings", model="hm")
    p = HostedEmbeddingProvider(client=client)
    assert p.name == "hosted"
    assert p.available is True
    assert p.model == "hm"
    assert p.get_sentence_embedding_dimension() == 4
    assert p.encode(["a", "b"]).shape == (2, 4)


def test_fastembed_adapter_delegates():
    client = _FakeClient(url="local://fastembed", model="all-MiniLM")
    p = FastEmbedEmbeddingProvider(client=client)
    assert p.name == "fastembed"
    assert p.available is True
    assert p.model == "all-MiniLM"
    assert p.encode(["a"]).shape == (1, 4)


def test_keyword_provider_is_unavailable():
    p = KeywordEmbeddingProvider()
    assert p.name == "keyword"
    assert p.available is False
    assert p.encode(["anything"]).size == 0
    assert p.get_sentence_embedding_dimension() == 0


def test_wrap_classifies_by_url():
    hosted = wrap_embedding_client(_FakeClient(url="http://x/v1/embeddings"))
    assert isinstance(hosted, HostedEmbeddingProvider)

    local = wrap_embedding_client(_FakeClient(url="local://fastembed"))
    assert isinstance(local, FastEmbedEmbeddingProvider)

    assert wrap_embedding_client(None) is None
