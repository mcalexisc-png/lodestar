"""Vector store interface for memory semantic search.

Documents the contract already satisfied by
``src.memory_vector.MemoryVectorStore`` (ChromaDB-backed). Phase 3 Step 2 adds
``src.sqlite_vec_store.SqliteVecMemoryStore`` as a second implementation —
both are interchangeable at the ``app_initializer`` injection point
(``memory_vector`` passed to ``NativeMemoryProvider`` and ``ChatProcessor``).

``memory.json`` (via ``MemoryManager``) remains the system of record for
memory text; a ``VectorStore`` is always a *rebuildable index* over that data,
never the source of truth. Implementations must degrade gracefully
(``healthy=False``) rather than raise when unavailable — callers fall back to
keyword search.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class VectorStore(Protocol):
    """Semantic index over memory entries, keyed by memory id."""

    @property
    def healthy(self) -> bool:
        """Whether this store is usable. ``False`` triggers keyword fallback."""

    def add(self, memory_id: str, text: str) -> None:
        """Index a single memory entry. Idempotent: a no-op if already indexed."""

    def remove(self, memory_id: str) -> None:
        """Remove a memory entry from the index."""

    def search(self, query: str, k: int = 8) -> List[Dict]:
        """Return up to ``k`` matches as ``[{"memory_id": str, "score": float}, ...]``.

        ``score`` is a similarity in roughly ``[0, 1]`` (higher = more
        similar), consistent across backends.
        """

    def find_similar(self, text: str, threshold: float = 0.92) -> Optional[str]:
        """Return the id of a near-duplicate entry, or ``None``."""

    def rebuild(self, memories: List[Dict]) -> None:
        """Rebuild the entire index from ``[{"id": str, "text": str}, ...]``."""

    def count(self) -> int:
        """Return the number of indexed entries."""

    def get_stats(self) -> Dict:
        """Return backend-specific diagnostics (at least ``healthy``/``count``)."""
