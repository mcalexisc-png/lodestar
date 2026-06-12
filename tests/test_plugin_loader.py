"""Tests for the in-process (Tier 2) plugin loader and the example plugin."""

import asyncio

import pytest

from src.plugins.loader import PluginLoader, PluginError
from src.plugins.manifest import Capability, PluginManifest


def _run(coro):
    return asyncio.run(coro)


# ── manifest ────────────────────────────────────────────────────────────────

def test_manifest_validate_requires_fields():
    with pytest.raises(ValueError):
        PluginManifest(name="", when_to_use="x", how="y").validate()
    with pytest.raises(ValueError):
        PluginManifest(name="t", when_to_use="", how="y").validate()


def test_manifest_schema_shape():
    m = PluginManifest(name="t", when_to_use="use it", how="pass input", tags=["a"])
    m.validate()
    schema = m.to_tool_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "t"
    assert "input" in schema["function"]["parameters"]["properties"]


def test_manifest_capabilities_normalized():
    m = PluginManifest(name="t", when_to_use="u", how="h", capabilities=["net", "fs"])
    m.validate()
    assert m.has_capability(Capability.NET)
    assert m.has_capability(Capability.FS)
    assert not m.has_capability(Capability.SHELL)


# ── loader with a fake bundled source ───────────────────────────────────────

def _fake_manifest(handler):
    return PluginManifest(
        name="fake_tool",
        when_to_use="when testing",
        how="pass input",
        tags=["test"],
        capabilities=[Capability.NET],
        handler=handler,
    )


@pytest.fixture
def loader(tmp_path, monkeypatch):
    ld = PluginLoader(state_file=str(tmp_path / "plugins.json"))
    # No entry points, inject one fake bundled manifest.
    monkeypatch.setattr(ld, "_iter_entry_points", staticmethod(lambda: []))

    handler_called = {}

    def handler(content, ctx):
        handler_called["content"] = content
        handler_called["caps"] = ctx.get("granted_capabilities")
        return {"output": f"ran:{content}", "exit_code": 0}

    monkeypatch.setattr(
        ld, "_iter_bundled_manifests",
        staticmethod(lambda: [(_fake_manifest(handler), "test:fake")]),
    )
    ld._handler_called = handler_called
    return ld


def test_discover_and_list(loader):
    plugins = loader.list_plugins()
    assert [p["name"] for p in plugins] == ["fake_tool"]
    assert plugins[0]["enabled"] is True
    assert plugins[0]["capabilities"] == ["net"]


def test_execute_runs_handler(loader):
    res = _run(loader.execute("fake_tool", "hello", {}))
    assert res == {"output": "ran:hello", "exit_code": 0}
    assert loader._handler_called["content"] == "hello"
    assert loader._handler_called["caps"] == {"net"}


def test_disable_blocks_execution(loader):
    loader.set_enabled("fake_tool", False)
    assert loader.is_enabled("fake_tool") is False
    res = _run(loader.execute("fake_tool", "x", {}))
    assert res["exit_code"] == 1
    assert "disabled" in res["error"]


def test_enable_disable_persists(loader, tmp_path):
    loader.set_enabled("fake_tool", False)
    # New loader pointed at the same state file sees the disabled flag.
    import json
    state = json.loads((tmp_path / "plugins.json").read_text())
    assert state["enabled"]["fake_tool"] is False


def test_unknown_tool(loader):
    res = _run(loader.execute("nope", "x", {}))
    assert res["exit_code"] == 1
    assert "Unknown plugin tool" in res["error"]


def test_set_enabled_unknown_raises(loader):
    with pytest.raises(PluginError):
        loader.set_enabled("nope", True)


def test_capability_guard_denies_undeclared(loader):
    """A plugin that didn't declare 'shell' is denied when it asks for it."""
    manifest = loader.get_manifest("fake_tool")
    from src.plugins.loader import _make_capability_guard

    guard = _make_capability_guard(manifest)
    guard("net")  # declared -> ok
    with pytest.raises(PermissionError):
        guard("shell")  # not declared -> denied


# ── lazy handler import via "module:attr" ───────────────────────────────────

def test_string_handler_lazy_import(tmp_path, monkeypatch):
    ld = PluginLoader(state_file=str(tmp_path / "plugins.json"))
    monkeypatch.setattr(ld, "_iter_entry_points", staticmethod(lambda: []))
    m = PluginManifest(
        name="textstats_proxy",
        when_to_use="u", how="h",
        handler="plugins.lodestar_textstats:run",
    )
    monkeypatch.setattr(ld, "_iter_bundled_manifests", staticmethod(lambda: [(m, "test")]))
    import json
    res = _run(ld.execute("textstats_proxy", json.dumps({"input": "a b c"}), {}))
    assert res["exit_code"] == 0
    assert res["stats"]["words"] == 3


# ── the real bundled example plugin ─────────────────────────────────────────

def test_real_example_plugin_discovered_and_runs():
    """The actual bundled text_stats plugin loads from the repo plugins/ dir."""
    import json

    ld = PluginLoader(state_file=None)
    names = ld.tool_names()
    assert "text_stats" in names
    res = _run(ld.execute("text_stats", json.dumps({"input": "Hello world. Bye!"}), {}))
    assert res["exit_code"] == 0
    assert res["stats"]["words"] == 3
    assert res["stats"]["sentences"] == 2
