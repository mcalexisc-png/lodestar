"""Tests for the Phase 3 memory vector backend selector.

Critical guarantee: lite mode without a hosted embedding endpoint must resolve
to keyword-only (no embedding provider, no vector store) so the idle-RSS
baseline is preserved.
"""

import numpy as np

from src.providers import selection


class _StubProvider:
    name = "stub"
    model = "stub-v1"
    available = True

    def get_sentence_embedding_dimension(self):
        return 4

    def encode(self, texts, normalize_embeddings=True):
        return np.ones((len(texts), 4), dtype="float32") / 2.0


def test_backend_choice_auto_prefers_sqlite_vec(monkeypatch):
    monkeypatch.delenv("LODESTAR_VECTOR_BACKEND", raising=False)
    monkeypatch.delenv("CHROMADB_HOST", raising=False)
    assert selection._vector_backend_choice({"vector_backend": "auto"}, lite=True) == "sqlite_vec"
    assert selection._vector_backend_choice({"vector_backend": "auto"}, lite=False) == "sqlite_vec"


def test_backend_choice_auto_uses_chromadb_when_host_set(monkeypatch):
    monkeypatch.delenv("LODESTAR_VECTOR_BACKEND", raising=False)
    monkeypatch.setenv("CHROMADB_HOST", "localhost")
    assert selection._vector_backend_choice({"vector_backend": "auto"}, lite=False) == "chromadb"


def test_backend_choice_env_override(monkeypatch):
    monkeypatch.setenv("LODESTAR_VECTOR_BACKEND", "chromadb")
    assert selection._vector_backend_choice({"vector_backend": "auto"}, lite=True) == "chromadb"
    monkeypatch.setenv("LODESTAR_VECTOR_BACKEND", "sqlite_vec")
    monkeypatch.setenv("CHROMADB_HOST", "localhost")
    assert selection._vector_backend_choice({}, lite=False) == "sqlite_vec"


def test_lite_without_hosted_endpoint_is_keyword_only(monkeypatch):
    """The baseline-preservation guarantee: no endpoint -> no embedder."""
    monkeypatch.delenv("EMBEDDING_URL", raising=False)
    monkeypatch.setattr(selection, "_hosted_endpoint_configured", lambda: False)
    assert selection.select_embedding_provider({}, lite=True) is None


def test_lite_with_hosted_endpoint_returns_provider(monkeypatch):
    monkeypatch.setattr(selection, "_hosted_endpoint_configured", lambda: True)
    sentinel = object()
    monkeypatch.setattr("src.embeddings.get_embedding_client", lambda: sentinel)
    assert selection.select_embedding_provider({}, lite=True) is sentinel


def test_select_vector_store_none_without_provider(monkeypatch):
    monkeypatch.delenv("LODESTAR_VECTOR_BACKEND", raising=False)
    monkeypatch.delenv("CHROMADB_HOST", raising=False)
    # sqlite_vec backend but no provider -> None (keyword fallback)
    assert selection.select_vector_store({"vector_backend": "sqlite_vec"}, lite=True, embedding_provider=None) is None


def test_select_vector_store_builds_sqlite_vec(monkeypatch, tmp_path):
    monkeypatch.delenv("LODESTAR_VECTOR_BACKEND", raising=False)
    monkeypatch.delenv("CHROMADB_HOST", raising=False)
    monkeypatch.setattr("src.constants.DATA_DIR", str(tmp_path))
    import src.providers.selection as sel  # re-import DATA_DIR inside the fn

    store = sel.select_vector_store(
        {"vector_backend": "sqlite_vec"}, lite=False, embedding_provider=_StubProvider()
    )
    # sqlite-vec may or may not be installed in the runner; if installed the
    # store is healthy, otherwise selection returns None gracefully.
    if store is not None:
        assert store.healthy is True
        assert store.get_stats()["backend"] == "sqlite-vec"
