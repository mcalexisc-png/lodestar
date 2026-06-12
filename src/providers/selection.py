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


def select_vector_store(settings: dict, lite: bool):
    """Return a ``VectorStore`` instance, or ``None`` for keyword-only memory.

    Placeholder for Step 2. Returning ``None`` preserves today's behavior:
    ``app_initializer`` falls back to keyword memory search when no vector
    store is available.
    """
    return None


def select_embedding_provider(settings: dict, lite: bool):
    """Return an ``EmbeddingProvider``, or ``None`` to use the legacy
    ``get_embedding_client()`` factory directly.

    Placeholder for Step 3.
    """
    return None


def select_search_provider(settings: dict, lite: bool) -> str:
    """Return the search provider name to use as the *primary* provider.

    Not yet called from ``services/search/core.py`` (Step 1 placeholder).
    Today, both modes use ``settings.get("search_provider", "searxng")``
    directly with no lite-specific branch. Step 4 wires this in and changes
    that: full mode keeps the ``"searxng"`` default; lite mode prefers the
    first API provider with a configured key (brave/tavily/exa), falling back
    to keyless ``"duckduckgo"`` — never SearXNG by default in lite.

    - If the admin has explicitly set ``search_provider`` to something other
      than the default ``"searxng"``, honor it unconditionally (explicit
      configuration always wins over the lite/full default).
    """
    configured = settings.get("search_provider", "searxng")
    if configured != "searxng":
        return configured

    if not lite:
        return "searxng"

    # Step 4 will replace this with key-aware selection across
    # brave/tavily/exa, falling back to duckduckgo.
    return "duckduckgo"
