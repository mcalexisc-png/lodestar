"""
sqlite_vec_store.py

Embedded vector store for memory entries, backed by the `sqlite-vec` loadable
SQLite extension. No external service (vs. the ChromaDB server) and no ONNX
runtime of its own — it just stores pre-computed embeddings from whatever
EmbeddingProvider the host hands it.

This is the lite/single-user default vector backend. It implements the same
surface as `src.memory_vector.MemoryVectorStore` (the
`src.providers.vectorstore.VectorStore` Protocol), so it drops in at the
`app_initializer` injection point with no changes to `NativeMemoryProvider` or
`ChatProcessor`.

Vectors live in a dedicated SQLite file (`data/vectors.db`), kept separate from
the primary `app.db` so the loadable extension and its `vec0` virtual tables
never touch application schema / migrations / WAL. `memory.json` remains the
system of record; this store is always a rebuildable index over it.
"""

import functools
import hashlib
import logging
import os
import sqlite3
import struct
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

#: vec0 virtual table holding the embeddings (cosine distance) + the sidecar
#: meta table holding the document text. vec0 stores only the pk + vector.
_VEC_TABLE = "vec_memories"
_META_TABLE = "vec_memories_meta"


def _serialize(vector) -> bytes:
    """Pack a float vector into the little-endian float32 blob vec0 expects."""
    return struct.pack("%df" % len(vector), *vector)


class SqliteVecMemoryStore:
    """Embedded vector index over memory entries.

    Mirrors `MemoryVectorStore`'s method surface:
    `healthy`, `add`, `remove`, `search`, `find_similar`, `rebuild`, `count`,
    `get_stats`.
    """

    def __init__(self, data_dir: str, embedding_provider):
        """
        Args:
            data_dir: directory for the vectors.db file (the app's DATA_DIR).
            embedding_provider: an object exposing `encode(texts) -> ndarray`
                and `get_sentence_embedding_dimension() -> int`. If it is None
                or cannot produce vectors, the store is unhealthy and callers
                fall back to keyword search.
        """
        self._provider = embedding_provider
        self._db_path = os.path.join(data_dir, "vectors.db")
        self._conn: Optional[sqlite3.Connection] = None
        self._dim: Optional[int] = None
        self._fingerprint: str = ""
        self._healthy = False
        self._initialize()

    # ── lifecycle ──────────────────────────────────────────────────────────

    def _provider_name(self) -> str:
        return getattr(self._provider, "name", None) or type(self._provider).__name__

    def _compute_fingerprint(self, dim: int) -> str:
        """sha256(provider|model|dim) — detects an incompatible model swap so a
        stale index of wrong-dimension vectors is rebuilt instead of queried."""
        model = getattr(self._provider, "model", "") or ""
        raw = f"{self._provider_name()}|{model}|{dim}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _initialize(self):
        if self._provider is None:
            logger.info("SqliteVecMemoryStore: no embedding provider; staying keyword-only")
            return
        if not getattr(self._provider, "available", True):
            logger.info("SqliteVecMemoryStore: embedding provider unavailable; staying keyword-only")
            return
        try:
            import sqlite_vec  # local import: only needed when this backend is selected
        except ImportError as e:
            logger.warning("SqliteVecMemoryStore: sqlite-vec not installed (%s); keyword fallback", e)
            return

        try:
            # Discover the embedding dimension up front (one probe call). If the
            # provider's endpoint is down this raises and we degrade to keyword.
            self._dim = int(self._provider.get_sentence_embedding_dimension())
            self._fingerprint = self._compute_fingerprint(self._dim)

            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-20000")
            conn.execute("PRAGMA mmap_size=134217728")
            conn.execute("PRAGMA busy_timeout=5000")
            self._conn = conn

            self._ensure_schema()
            self._healthy = True
            logger.info(
                "SqliteVecMemoryStore ready (dim=%s provider=%s entries=%s db=%s)",
                self._dim, self._provider_name(), self.count(), self._db_path,
            )
        except Exception as e:
            logger.warning("SqliteVecMemoryStore init failed (%s); keyword fallback", e)
            self._healthy = False
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    def _ensure_schema(self):
        """Create the vec0 + meta tables, rebuilding if the embedding model
        fingerprint changed (incompatible dimensions/model)."""
        conn = self._conn
        # Track which fingerprint the current index was built with.
        conn.execute(
            "CREATE TABLE IF NOT EXISTS vec_meta_info (key TEXT PRIMARY KEY, value TEXT)"
        )
        stored_fp_row = conn.execute(
            "SELECT value FROM vec_meta_info WHERE key='fingerprint'"
        ).fetchone()
        stored_fp = stored_fp_row[0] if stored_fp_row else None

        vec_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (_VEC_TABLE,)
        ).fetchone()

        if vec_exists and stored_fp and stored_fp != self._fingerprint:
            logger.info(
                "SqliteVecMemoryStore: embedding fingerprint changed (%s -> %s); "
                "dropping stale index for rebuild",
                stored_fp, self._fingerprint,
            )
            conn.execute(f"DROP TABLE IF EXISTS {_VEC_TABLE}")
            conn.execute(f"DROP TABLE IF EXISTS {_META_TABLE}")
            vec_exists = None

        if not vec_exists:
            conn.execute(
                f"CREATE VIRTUAL TABLE {_VEC_TABLE} USING vec0("
                f"memory_id TEXT PRIMARY KEY, "
                f"embedding FLOAT[{self._dim}] distance_metric=cosine)"
            )
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {_META_TABLE} ("
                f"memory_id TEXT PRIMARY KEY, text TEXT)"
            )
        conn.execute(
            "INSERT OR REPLACE INTO vec_meta_info (key, value) VALUES ('fingerprint', ?)",
            (self._fingerprint,),
        )
        conn.commit()

    # ── VectorStore Protocol ────────────────────────────────────────────────

    @property
    def healthy(self) -> bool:
        return self._healthy

    @functools.lru_cache(maxsize=256)
    def _embed_one(self, text: str):
        vecs = self._provider.encode([text])
        if vecs is None or len(vecs) == 0:
            return None
        return vecs[0].tolist()

    def count(self) -> int:
        if not self._healthy:
            return 0
        try:
            row = self._conn.execute(f"SELECT COUNT(*) FROM {_VEC_TABLE}").fetchone()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    def add(self, memory_id: str, text: str):
        if not self._healthy or not memory_id or not text:
            return
        try:
            existing = self._conn.execute(
                f"SELECT 1 FROM {_VEC_TABLE} WHERE memory_id=?", (memory_id,)
            ).fetchone()
            if existing:
                return  # idempotent, matches MemoryVectorStore.add
            vec = self._embed_one(text)
            if vec is None:
                return
            self._conn.execute(
                f"INSERT INTO {_VEC_TABLE}(memory_id, embedding) VALUES (?, ?)",
                (memory_id, _serialize(vec)),
            )
            self._conn.execute(
                f"INSERT OR REPLACE INTO {_META_TABLE}(memory_id, text) VALUES (?, ?)",
                (memory_id, text),
            )
            self._conn.commit()
        except Exception as e:
            logger.warning("sqlite-vec memory add failed for %s: %s", memory_id, e)

    def remove(self, memory_id: str):
        if not self._healthy:
            return
        try:
            self._conn.execute(f"DELETE FROM {_VEC_TABLE} WHERE memory_id=?", (memory_id,))
            self._conn.execute(f"DELETE FROM {_META_TABLE} WHERE memory_id=?", (memory_id,))
            self._conn.commit()
        except Exception as e:
            logger.warning("sqlite-vec memory remove %s: %s", memory_id, e)

    def search(self, query: str, k: int = 8) -> List[Dict]:
        """Return [{"memory_id", "score"}] sorted by descending similarity.

        sqlite-vec cosine `distance` = 1 - cosine_similarity, so
        similarity = 1 - distance, matching MemoryVectorStore.search exactly.
        """
        if not self._healthy or self.count() == 0:
            return []
        try:
            vec = self._embed_one(query)
            if vec is None:
                return []
            limit = min(k, self.count())
            rows = self._conn.execute(
                f"SELECT memory_id, distance FROM {_VEC_TABLE} "
                f"WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
                (_serialize(vec), limit),
            ).fetchall()
            return [
                {"memory_id": mid, "score": round(1.0 - distance, 4)}
                for mid, distance in rows
            ]
        except Exception as e:
            logger.warning("sqlite-vec memory search failed: %s", e)
            return []

    def find_similar(self, text: str, threshold: float = 0.92) -> Optional[str]:
        """Return the id of a near-duplicate (cosine similarity >= threshold)."""
        if not self._healthy or self.count() == 0:
            return None
        try:
            vec = self._embed_one(text)
            if vec is None:
                return None
            row = self._conn.execute(
                f"SELECT memory_id, distance FROM {_VEC_TABLE} "
                f"WHERE embedding MATCH ? ORDER BY distance LIMIT 1",
                (_serialize(vec),),
            ).fetchone()
            if row and (1.0 - row[1]) >= threshold:
                return row[0]
        except Exception as e:
            logger.warning("sqlite-vec memory similarity failed: %s", e)
        return None

    def rebuild(self, memories: List[Dict]):
        """Rebuild the entire index from `[{"id", "text"}, ...]`.

        Embeds in batches off the caller's hot path (the provider's encode is
        itself batched). Clears the existing index first.
        """
        if not self._healthy:
            return
        try:
            self._conn.execute(f"DELETE FROM {_VEC_TABLE}")
            self._conn.execute(f"DELETE FROM {_META_TABLE}")

            pairs = [
                (m.get("id", ""), (m.get("text") or "").strip())
                for m in memories
            ]
            pairs = [(mid, text) for mid, text in pairs if mid and text]

            for i in range(0, len(pairs), 100):
                batch = pairs[i:i + 100]
                texts = [text for _mid, text in batch]
                vecs = self._provider.encode(texts)
                for (mid, text), vec in zip(batch, vecs):
                    self._conn.execute(
                        f"INSERT INTO {_VEC_TABLE}(memory_id, embedding) VALUES (?, ?)",
                        (mid, _serialize(vec.tolist())),
                    )
                    self._conn.execute(
                        f"INSERT OR REPLACE INTO {_META_TABLE}(memory_id, text) VALUES (?, ?)",
                        (mid, text),
                    )
            self._conn.commit()
            self._embed_one.cache_clear()
            logger.info("SqliteVecMemoryStore rebuilt with %s entries", len(pairs))
        except Exception as e:
            logger.warning("sqlite-vec memory rebuild failed: %s", e)

    def get_stats(self) -> Dict:
        return {
            "healthy": self._healthy,
            "count": self.count(),
            "backend": "sqlite-vec",
            "dimension": self._dim,
            "provider": self._provider_name() if self._provider else None,
            "db_path": self._db_path,
        }
