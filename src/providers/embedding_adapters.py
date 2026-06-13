"""Concrete embedding providers behind the EmbeddingProvider Protocol.

Three adapters:

- ``HostedEmbeddingProvider`` — wraps the existing ``EmbeddingClient``
  (OpenAI-compatible ``/v1/embeddings`` via ``EMBEDDING_URL``). Zero local
  compute; the ideal low-end path.
- ``FastEmbedEmbeddingProvider`` — wraps the existing ``FastEmbedClient``
  (local ONNX). Lazy: the heavy ``fastembed`` import only happens when this
  adapter is actually constructed/used.
- ``KeywordEmbeddingProvider`` — a no-vector sentinel. ``available`` is
  ``False`` and ``encode`` returns an empty array, so callers uniformly treat
  "no embeddings configured" the same as "endpoint down": memory falls back to
  keyword search. Exists so selection can return an object instead of ``None``
  when a caller prefers that.

The hosted/fastembed wrappers delegate to the underlying client's ``encode``
and ``get_sentence_embedding_dimension`` (which already match the Protocol
structurally); the wrappers add the ``name``/``available`` attributes and a
stable ``model`` for the vector-store fingerprint.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class HostedEmbeddingProvider:
    """OpenAI-compatible hosted embeddings (``EMBEDDING_URL``)."""

    name = "hosted"
    available = True

    def __init__(self, client=None):
        if client is None:
            from src.embeddings import EmbeddingClient

            client = EmbeddingClient()
        self._client = client
        self.model = getattr(client, "model", "") or ""
        self.url = getattr(client, "url", "")

    def encode(self, texts: List[str], normalize_embeddings: bool = True) -> np.ndarray:
        return self._client.encode(texts, normalize_embeddings=normalize_embeddings)

    def get_sentence_embedding_dimension(self) -> int:
        return self._client.get_sentence_embedding_dimension()


class FastEmbedEmbeddingProvider:
    """Local ONNX embeddings via fastembed. Heavy; constructed lazily."""

    name = "fastembed"
    available = True

    def __init__(self, client=None):
        if client is None:
            from src.embeddings import FastEmbedClient

            client = FastEmbedClient()
        self._client = client
        self.model = getattr(client, "model", "") or ""
        self.url = getattr(client, "url", "local://fastembed")

    def encode(self, texts: List[str], normalize_embeddings: bool = True) -> np.ndarray:
        return self._client.encode(texts, normalize_embeddings=normalize_embeddings)

    def get_sentence_embedding_dimension(self) -> int:
        return self._client.get_sentence_embedding_dimension()


class KeywordEmbeddingProvider:
    """No-vector sentinel: signals that embeddings are unavailable.

    Used when nothing hosted is configured and local ONNX is disallowed (lite
    mode). Memory uses its keyword fallback when given this provider (or None).
    """

    name = "keyword"
    available = False
    model = ""
    url = "none://keyword"

    def encode(self, texts: List[str], normalize_embeddings: bool = True) -> np.ndarray:
        return np.array([], dtype="float32")

    def get_sentence_embedding_dimension(self) -> int:
        return 0


def wrap_embedding_client(client) -> Optional[object]:
    """Classify a client returned by ``get_embedding_client()`` into the right
    Protocol adapter. Returns ``None`` if ``client`` is ``None``.
    """
    if client is None:
        return None
    # FastEmbedClient advertises url="local://fastembed".
    if getattr(client, "url", "").startswith("local://"):
        return FastEmbedEmbeddingProvider(client=client)
    return HostedEmbeddingProvider(client=client)
