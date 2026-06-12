"""Web search provider interface.

Documents the contract already satisfied by the provider functions in
``services/search/providers.py`` (``searxng_search_api``, ``brave_search``,
``duckduckgo_search``, ``google_pse_search``, ``tavily_search``,
``serper_search``) and dispatched by ``_call_provider`` in
``services/search/core.py``. Phase 3 Step 4 adds an Exa adapter and a
``select_search_provider`` helper that picks an API provider over SearXNG in
lite mode.
"""

from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable


@runtime_checkable
class SearchProvider(Protocol):
    """A web search backend."""

    #: Registry key, e.g. "searxng", "brave", "duckduckgo", "tavily", "exa".
    name: str

    #: Whether this provider requires a user-supplied API key.
    needs_key: bool

    #: Whether this provider requires a configured instance URL (SearXNG).
    needs_url: bool

    def search(self, query: str, count: int, time_filter: Optional[str] = None) -> List[dict]:
        """Return a list of result dicts (provider-specific shape, normalized
        by ``services.search.core``). Return ``[]`` on failure rather than
        raising — callers rely on the provider chain to fall back.
        """
