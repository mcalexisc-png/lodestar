"""Tests for the embedded sqlite-vec memory vector store.

Uses a deterministic fake embedding provider (no network, no ONNX) so the
tests are CI-safe and assert retrieval quality against a known cosine ordering.
"""

import math

import numpy as np
import pytest

sqlite_vec = pytest.importorskip("sqlite_vec")

from src.sqlite_vec_store import SqliteVecMemoryStore  # noqa: E402


class FakeEmbeddingProvider:
    """Maps a small fixed vocabulary to orthogonal-ish unit vectors.

    Each text is embedded as the L2-normalized sum of its word vectors, so
    cosine similarity tracks word overlap — deterministic and inspectable.
    """

    name = "fake"
    model = "fake-v1"
    available = True

    _VOCAB = ["cat", "dog", "car", "boat", "python", "java", "coffee", "tea"]

    def __init__(self):
        self._dim = len(self._VOCAB)
        self._index = {w: i for i, w in enumerate(self._VOCAB)}

    def get_sentence_embedding_dimension(self):
        return self._dim

    def encode(self, texts, normalize_embeddings=True):
        out = []
        for text in texts:
            vec = np.zeros(self._dim, dtype="float32")
            for word in text.lower().split():
                idx = self._index.get(word)
                if idx is not None:
                    vec[idx] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            out.append(vec)
        return np.array(out, dtype="float32")


@pytest.fixture
def store(tmp_path):
    return SqliteVecMemoryStore(str(tmp_path), FakeEmbeddingProvider())


def test_store_is_healthy_with_provider(store):
    assert store.healthy is True
    assert store.get_stats()["backend"] == "sqlite-vec"
    assert store.get_stats()["dimension"] == 8


def test_keyword_fallback_when_no_provider(tmp_path):
    store = SqliteVecMemoryStore(str(tmp_path), embedding_provider=None)
    assert store.healthy is False
    assert store.search("anything") == []
    assert store.count() == 0


def test_add_and_search_orders_by_similarity(store):
    store.add("m1", "cat dog")
    store.add("m2", "python java")
    store.add("m3", "coffee tea")
    assert store.count() == 3

    hits = store.search("cat", k=3)
    assert hits, "expected at least one hit"
    # The pet memory must rank first for a pet query.
    assert hits[0]["memory_id"] == "m1"
    # Scores are cosine similarities in [0, 1].
    for hit in hits:
        assert 0.0 <= hit["score"] <= 1.0001
    # Exact-overlap query against "cat dog" -> cosine of "cat" vs (cat+dog)/√2
    # = 1/√2 ≈ 0.7071.
    assert math.isclose(hits[0]["score"], 1 / math.sqrt(2), abs_tol=1e-3)


def test_add_is_idempotent(store):
    store.add("m1", "cat dog")
    store.add("m1", "cat dog")
    assert store.count() == 1


def test_remove(store):
    store.add("m1", "cat dog")
    store.add("m2", "python java")
    store.remove("m1")
    assert store.count() == 1
    hits = store.search("cat", k=5)
    assert all(h["memory_id"] != "m1" for h in hits)


def test_find_similar(store):
    store.add("m1", "python java")
    # Identical text -> cosine 1.0 >= threshold.
    assert store.find_similar("python java", threshold=0.92) == "m1"
    # Unrelated text -> no near-duplicate.
    assert store.find_similar("coffee tea", threshold=0.92) is None


def test_rebuild_from_memory_list(store):
    store.add("old", "cat dog")
    store.rebuild([
        {"id": "a", "text": "python java"},
        {"id": "b", "text": "coffee tea"},
        {"id": "c", "text": ""},  # skipped (no text)
    ])
    assert store.count() == 2
    hits = store.search("python", k=2)
    assert hits[0]["memory_id"] == "a"


def test_search_matches_reference_cosine_ordering(store):
    docs = {
        "pets": "cat dog",
        "langs": "python java",
        "drinks": "coffee tea",
        "vehicles": "car boat",
    }
    for mid, text in docs.items():
        store.add(mid, text)

    provider = FakeEmbeddingProvider()
    # "python java coffee" overlaps "langs" on 2 words but "drinks" on only 1,
    # so there is a strict (untied) best match.
    query = "python java coffee"
    qv = provider.encode([query])[0]

    # Reference cosine scores computed independently.
    ref = {}
    for mid, text in docs.items():
        dv = provider.encode([text])[0]
        ref[mid] = float(np.dot(qv, dv))
    best = max(ref, key=ref.get)
    assert best == "langs"  # sanity: the reference itself is unambiguous

    hits = store.search(query, k=len(docs))
    got_order = [h["memory_id"] for h in hits]
    # Top result must agree with the reference best match.
    assert got_order[0] == best
    # And the returned scores must match the reference cosine within rounding.
    got_scores = {h["memory_id"]: h["score"] for h in hits}
    for mid, score in got_scores.items():
        assert math.isclose(score, ref[mid], abs_tol=1e-3)


def test_fingerprint_change_triggers_rebuild(tmp_path):
    # Build an index with one provider/model.
    store1 = SqliteVecMemoryStore(str(tmp_path), FakeEmbeddingProvider())
    store1.add("m1", "cat dog")
    assert store1.count() == 1

    # Re-open with a different model fingerprint -> stale index dropped.
    provider2 = FakeEmbeddingProvider()
    provider2.model = "fake-v2"
    store2 = SqliteVecMemoryStore(str(tmp_path), provider2)
    assert store2.healthy is True
    assert store2.count() == 0  # rebuilt empty because fingerprint changed
