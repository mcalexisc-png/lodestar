"""API-level tests for the plugin routes via httpx ASGITransport.

Mounts only the plugin router on a fresh FastAPI app with auth disabled, so the
test exercises the real route + plugin loader without booting the whole app.
"""

import asyncio
import os

import httpx
import pytest


def _make_app():
    from fastapi import FastAPI

    from routes.plugin_routes import setup_plugin_routes

    app = FastAPI()
    app.include_router(setup_plugin_routes())
    return app


def _get(app, url):
    async def _run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(url)

    return asyncio.run(_run())


@pytest.fixture(autouse=True)
def _env_and_loader(monkeypatch):
    # Disable auth for the route (restored automatically by monkeypatch), and
    # reset the loader singleton so enable/disable from other tests doesn't leak.
    monkeypatch.setenv("AUTH_ENABLED", "false")
    import src.plugins.loader as loader_mod

    monkeypatch.setattr(loader_mod, "_loader", None)
    yield
    monkeypatch.setattr(loader_mod, "_loader", None)


def test_list_plugins_route():
    app = _make_app()
    resp = _get(app, "/api/plugins")
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()["plugins"]]
    assert "text_stats" in names


def test_panels_route_returns_sanitized_panels():
    app = _make_app()
    resp = _get(app, "/api/plugins/panels")
    assert resp.status_code == 200
    panels = resp.json()["panels"]
    by_plugin = {p["plugin"]: p for p in panels}
    assert "text_stats" in by_plugin
    panel = by_plugin["text_stats"]
    assert panel["type"] == "schema"
    allowed = {"heading", "text", "list", "key_value", "link", "badge"}
    assert all(w["type"] in allowed for w in panel["widgets"])
