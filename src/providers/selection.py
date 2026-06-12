"""Backend selection: pick a concrete provider based on settings/lite mode.

These functions are the single seam that ``LODESTAR_LITE`` and admin settings
flow through to choose a vector store, embedding provider, or search
provider. They centralize the decision so it isn't scattered as ``if LITE:``
checks across ``app_initializer``, ``services/search``, etc.

Step 1 introduces this module with the function signatures and documents the
intended selection logic; **none of these are wired into the runtime yet**, so
behavior is unchanged. Steps 2-4 wire each one in:

- ``select_vector_store`` — wired into ``app_initializer`` by Step 2.
- ``select_embedding_provider`` — wired into the embedding factory by Step 3.
- ``select_search_provider`` — wired into ``services/search/core.py`` by
  Step 4 (this is also where lite's search default changes from "SearXNG with
  duckduckgo fallback" to "an API provider primary").
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _vector_backend_choice(settings: dict, lite: bool) -> str:
    """Resolve the ``vector_backend`` setting to a concrete backend name.

    Values: ``"auto" | "sqlite_vec" | "chromadb"``. ``LODESTAR_VECTOR_BACKEND``
    env var overrides the setting. ``"auto"`` resolves to:

    - ``"chromadb"`` if a ChromaDB host is *explicitly* configured (env
      ``CHROMADB_HOST`` set) — preserves full/multi-user setups.
    - else ``"sqlite_vec"`` — the embedded single-user default (lite + the
      common full-mode case where no ChromaDB server is configured).
    """
    import os

    choice = (os.getenv("LODESTAR_VECTOR_BACKEND") or settings.get("vector_backend") or "auto").lower()
    if choice in ("sqlite_vec", "chromadb"):
        return choice
    # auto
    if os.getenv("CHROMADB_HOST"):
        return "chromadb"
    return "sqlite_vec"


def select_vector_store(settings: dict, lite: bool, embedding_provider=None):
    """Return a ``VectorStore`` instance, or ``None`` for keyword-only memory.

    - ``sqlite_vec``: embedded store in ``data/vectors.db``. Needs an embedding
      provider; if none is available (e.g. lite mode with no hosted endpoint),
      returns ``None`` and memory stays keyword-only — so idle RSS does not
      regress (no ONNX is loaded just to populate an embedded index).
    - ``chromadb``: the existing server-backed ``MemoryVectorStore`` (full /
      multi-user). Unchanged behavior; returns ``None`` if it can't connect so
      callers degrade to keyword search exactly as before.
    """
    from src.constants import DATA_DIR

    backend = _vector_backend_choice(settings, lite)

    if backend == "chromadb":
        try:
            from src.memory_vector import MemoryVectorStore

            store = MemoryVectorStore(DATA_DIR)
            return store if store.healthy else None
        except Exception as e:
            logger.warning("ChromaDB memory vector store unavailable (%s); keyword fallback", e)
            return None

    # sqlite_vec
    if embedding_provider is None or not getattr(embedding_provider, "available", True):
        logger.info(
            "Embedded vector store: no embedding provider available "
            "(lite=%s); using keyword memory search", lite,
        )
        return None
    try:
        from src.sqlite_vec_store import SqliteVecMemoryStore

        store = SqliteVecMemoryStore(DATA_DIR, embedding_provider)
        return store if store.healthy else None
    except Exception as e:
        logger.warning("Embedded sqlite-vec store unavailable (%s); keyword fallback", e)
        return None


def _hosted_endpoint_configured() -> bool:
    """Whether a hosted embedding endpoint is configured (env or admin panel).

    Lite mode only loads an embedder when one of these is set — it never falls
    back to local fastembed/ONNX, which would regress idle RSS.
    """
    import os

    if os.getenv("EMBEDDING_URL"):
        return True
    try:
        from src.embeddings import _load_persisted_endpoint

        return bool(_load_persisted_endpoint().get("url"))
    except Exception:
        return False


def select_embedding_provider(settings: dict, lite: bool):
    """Return an ``EmbeddingProvider`` adapter, or ``None`` for keyword-only.

    - Lite: a ``HostedEmbeddingProvider`` **only if** a hosted endpoint is
      configured; otherwise ``None`` (no local ONNX load → idle RSS
      unchanged). Lite never constructs the fastembed adapter.
    - Full: hosted if reachable, else local fastembed — today's behavior,
      delegated to the existing ``get_embedding_client()`` factory (HTTP-down
      latch, persisted-endpoint logic) and classified into the matching
      adapter.

    The returned object exposes ``name``/``available``/``model`` on top of the
    ``encode`` + ``get_sentence_embedding_dimension`` contract, so the vector
    store can fingerprint it and callers can check availability uniformly.
    """
    from src.providers.embedding_adapters import (
        HostedEmbeddingProvider,
        wrap_embedding_client,
    )

    if lite:
        if not _hosted_endpoint_configured():
            return None
        # Lite: hosted only, never fall back to local ONNX.
        try:
            return HostedEmbeddingProvider()
        except Exception as e:
            logger.warning("hosted embedding provider unavailable in lite (%s); keyword fallback", e)
            return None

    try:
        from src.embeddings import get_embedding_client

        return wrap_embedding_client(get_embedding_client())
    except Exception as e:
        logger.warning("embedding provider selection failed (%s); keyword fallback", e)
        return None


#: Lite-mode preference order among key-based API providers. First one with a
#: configured key wins; otherwise lite falls back to keyless DuckDuckGo. Never
#: SearXNG by default in lite (it needs a running container).
_LITE_API_PROVIDER_ORDER = ("brave", "tavily", "exa")


def select_search_provider(settings: dict, lite: bool) -> str:
    """Return the search provider name to use as the *primary* provider.

    - If the admin has explicitly set ``search_provider`` to something other
      than the default ``"searxng"``, honor it unconditionally (explicit
      configuration always wins over the lite/full default).
    - Full mode keeps the documented ``"searxng"`` default.
    - Lite mode prefers the first API provider with a configured key
      (brave → tavily → exa), falling back to keyless ``"duckduckgo"`` — so it
      never depends on the SearXNG container.
    """
    configured = settings.get("search_provider", "searxng")
    if configured != "searxng":
        return configured

    if not lite:
        return "searxng"

    try:
        from services.search.providers import _get_provider_key

        for provider in _LITE_API_PROVIDER_ORDER:
            if _get_provider_key(provider):
                return provider
    except Exception as e:
        logger.warning("lite search provider key probe failed (%s); using duckduckgo", e)
    return "duckduckgo"
