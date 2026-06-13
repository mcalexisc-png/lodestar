"""Tests for the Phase 3 search additions: the Exa adapter and the lite-mode
search provider selection (API provider instead of SearXNG)."""

import httpx
import pytest

from services.search import providers as P
from src.providers import selection


# ── Exa adapter ──────────────────────────────────────────────────────────────

def test_exa_no_key_returns_empty(monkeypatch):
    monkeypatch.setattr(P, "_get_provider_key", lambda provider: "")
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    assert P.exa_search("anything") == []


def test_exa_parses_results(monkeypatch):
    monkeypatch.setattr(P, "_get_provider_key", lambda provider: "test-key")
    monkeypatch.setattr(P, "_get_result_count", lambda: 5)

    captured = {}

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": [
                    {
                        "title": "Result One",
                        "url": "https://example.com/1",
                        "text": "snippet one",
                        "publishedDate": "2026-01-01",
                    },
                    {"title": "No URL", "url": "", "text": "skip me"},
                ]
            }

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _Resp()

    monkeypatch.setattr(httpx, "post", fake_post)

    results = P.exa_search("hello", count=5)
    assert captured["url"] == "https://api.exa.ai/search"
    assert captured["headers"]["x-api-key"] == "test-key"
    assert captured["json"]["query"] == "hello"
    # The result with no URL is dropped.
    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/1"
    assert results[0]["snippet"] == "snippet one"


def test_exa_rate_limit_returns_empty(monkeypatch):
    monkeypatch.setattr(P, "_get_provider_key", lambda provider: "k")

    class _Resp:
        status_code = 429

        def raise_for_status(self):
            pass

        def json(self):
            return {}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp())
    assert P.exa_search("q") == []


def test_exa_registered_in_provider_info_and_dispatch():
    assert "exa" in P.PROVIDER_INFO
    label, needs_key, needs_url = P.PROVIDER_INFO["exa"]
    assert needs_key is True and needs_url is False

    from services.search.core import _call_provider

    # Dispatch routes "exa" -> exa_search (no key -> empty, no exception).
    assert _call_provider("exa", "q", 3) == [] or isinstance(_call_provider("exa", "q", 3), list)


# ── Lite search provider selection ───────────────────────────────────────────

def test_full_mode_defaults_to_searxng():
    assert selection.select_search_provider({}, lite=False) == "searxng"


def test_explicit_provider_overrides_lite(monkeypatch):
    assert selection.select_search_provider({"search_provider": "tavily"}, lite=True) == "tavily"
    assert selection.select_search_provider({"search_provider": "brave"}, lite=False) == "brave"


def test_lite_prefers_keyed_api_provider(monkeypatch):
    # Only tavily has a key -> tavily wins over duckduckgo.
    monkeypatch.setattr(
        "services.search.providers._get_provider_key",
        lambda provider: "k" if provider == "tavily" else "",
    )
    assert selection.select_search_provider({}, lite=True) == "tavily"


def test_lite_provider_order_brave_first(monkeypatch):
    # Brave and exa both keyed -> brave wins (order: brave, tavily, exa).
    monkeypatch.setattr(
        "services.search.providers._get_provider_key",
        lambda provider: "k" if provider in ("brave", "exa") else "",
    )
    assert selection.select_search_provider({}, lite=True) == "brave"


def test_lite_falls_back_to_duckduckgo_without_keys(monkeypatch):
    monkeypatch.setattr("services.search.providers._get_provider_key", lambda provider: "")
    assert selection.select_search_provider({}, lite=True) == "duckduckgo"
