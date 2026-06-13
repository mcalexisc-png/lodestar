"""Embedding provider interface.

Documents the contract already satisfied by ``src.embeddings.EmbeddingClient``
(hosted, OpenAI-compatible ``/v1/embeddings``) and
``src.embeddings.FastEmbedClient`` (local ONNX). Phase 3 Step 3 adds a
keyword-only implementation that satisfies this Protocol by reporting
unavailability (no vectors), so callers can treat "no embeddings configured"
uniformly with "embeddings configured but the endpoint is down".
"""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class EmbeddingProvider(Protocol):
    """A backend that turns text into embedding vectors."""

    #: Short identifier used in logs/diagnostics, e.g. "hosted", "fastembed",
    #: "keyword".
    name: str

    def encode(self, texts: List[str], normalize_embeddings: bool = True) -> np.ndarray:
        """Encode ``texts`` into a ``(N, dim)`` float32 array.

        Implementations that cannot produce vectors (e.g. keyword-only)
        return an empty array; callers should check :attr:`available` first.
        """

    def get_sentence_embedding_dimension(self) -> int:
        """Return the embedding dimension, probing the backend if needed."""

    @property
    def available(self) -> bool:
        """Whether this provider can produce real vectors.

        ``EmbeddingClient`` and ``FastEmbedClient`` are always ``True`` once
        constructed (construction itself fails if the backend is
        unreachable). A keyword-only provider is always ``False`` — it exists
        so callers have a uniform object to hold instead of ``None``.
        """
