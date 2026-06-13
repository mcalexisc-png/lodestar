"""Tests for safe plugin UI panel sanitization.

The security property under test: a plugin can only produce panels from the
fixed widget vocabulary or a sandboxed iframe — never arbitrary markup/JS.
"""

from src.plugins.manifest import PluginManifest


def _manifest(panel):
    return PluginManifest(name="p", when_to_use="u", how="h", panel=panel)


def test_no_panel_returns_none():
    assert _manifest(None).sanitized_panel() is None
    assert _manifest({}).sanitized_panel() is None


def test_schema_panel_keeps_allowed_widgets():
    m = _manifest({
        "type": "schema",
        "title": "T",
        "widgets": [
            {"type": "heading", "text": "H"},
            {"type": "text", "text": "body"},
            {"type": "list", "items": ["a", "b"]},
            {"type": "key_value", "pairs": {"k": "v"}},
            {"type": "link", "text": "site", "href": "https://x"},
            {"type": "badge", "text": "b"},
        ],
    })
    panel = m.sanitized_panel()
    assert panel["type"] == "schema"
    assert panel["title"] == "T"
    assert panel["plugin"] == "p"
    types = [w["type"] for w in panel["widgets"]]
    assert types == ["heading", "text", "list", "key_value", "link", "badge"]


def test_schema_panel_drops_unknown_widget_types():
    m = _manifest({
        "type": "schema",
        "widgets": [
            {"type": "script", "text": "alert(1)"},   # not allowlisted -> dropped
            {"type": "html", "text": "<img onerror=x>"},  # dropped
            {"type": "heading", "text": "ok"},
        ],
    })
    panel = m.sanitized_panel()
    assert [w["type"] for w in panel["widgets"]] == ["heading"]


def test_schema_widget_values_are_stringified():
    m = _manifest({
        "type": "schema",
        "widgets": [{"type": "list", "items": [1, 2, {"x": 1}]}],
    })
    panel = m.sanitized_panel()
    assert all(isinstance(i, str) for i in panel["widgets"][0]["items"])


def test_iframe_panel_normalized():
    m = _manifest({"type": "iframe", "title": "Frame", "url": "https://x.example", "height": 99999})
    panel = m.sanitized_panel()
    assert panel["type"] == "iframe"
    assert panel["url"] == "https://x.example"
    # Height clamped to the [120, 1200] range.
    assert panel["height"] == 1200


def test_iframe_without_url_is_none():
    assert _manifest({"type": "iframe", "title": "x"}).sanitized_panel() is None


def test_unknown_panel_type_is_none():
    assert _manifest({"type": "magic", "title": "x"}).sanitized_panel() is None


def test_loader_panels_collects_enabled(tmp_path, monkeypatch):
    from src.plugins.loader import PluginLoader

    ld = PluginLoader(state_file=str(tmp_path / "plugins.json"))
    monkeypatch.setattr(ld, "_iter_entry_points", staticmethod(lambda: []))
    m = PluginManifest(
        name="withpanel", when_to_use="u", how="h",
        panel={"type": "schema", "title": "P", "widgets": [{"type": "text", "text": "hi"}]},
    )
    m2 = PluginManifest(name="nopanel", when_to_use="u", how="h")
    monkeypatch.setattr(
        ld, "_iter_bundled_manifests",
        staticmethod(lambda: [(m, "t1"), (m2, "t2")]),
    )
    panels = ld.panels()
    assert [p["plugin"] for p in panels] == ["withpanel"]

    # Disabled plugins contribute no panel.
    ld.set_enabled("withpanel", False)
    assert ld.panels() == []


def test_real_example_plugin_has_safe_panel():
    from src.plugins.loader import PluginLoader

    ld = PluginLoader(state_file=None)
    panels = {p["plugin"]: p for p in ld.panels()}
    assert "text_stats" in panels
    panel = panels["text_stats"]
    assert panel["type"] == "schema"
    assert all(w["type"] in {"heading", "text", "list", "key_value", "link", "badge"}
               for w in panel["widgets"])
