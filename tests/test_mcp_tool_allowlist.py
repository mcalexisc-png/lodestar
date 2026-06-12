"""Tests for the Phase 3 MCP per-tool allow/deny policy enforcement."""

import asyncio

from src.mcp_manager import McpManager


def _run(coro):
    return asyncio.run(coro)


def test_no_policy_provider_allows(monkeypatch):
    mgr = McpManager()
    # No session registered -> reaches the "not connected" path, proving policy
    # didn't short-circuit with a block.
    res = _run(mgr.call_tool("mcp__srv__do_thing", {}))
    assert "not connected" in res["error"]


def test_denylist_blocks_at_runtime():
    mgr = McpManager()
    mgr.set_tool_policy_provider(
        lambda: {"srv": {"disabled": {"danger"}, "allowed": None}}
    )
    res = _run(mgr.call_tool("mcp__srv__danger", {}))
    assert res["exit_code"] == 1
    assert "disabled by admin policy" in res["error"]


def test_allowlist_blocks_non_listed_tool():
    mgr = McpManager()
    mgr.set_tool_policy_provider(
        lambda: {"srv": {"disabled": set(), "allowed": {"safe_tool"}}}
    )
    res = _run(mgr.call_tool("mcp__srv__other_tool", {}))
    assert res["exit_code"] == 1
    assert "not in the admin allowlist" in res["error"]


def test_allowlist_permits_listed_tool_reaches_session_check():
    mgr = McpManager()
    mgr.set_tool_policy_provider(
        lambda: {"srv": {"disabled": set(), "allowed": {"safe_tool"}}}
    )
    # Allowed -> passes policy, then fails on "not connected" (no session).
    res = _run(mgr.call_tool("mcp__srv__safe_tool", {}))
    assert "not connected" in res["error"]


def test_disabled_wins_over_allowed():
    mgr = McpManager()
    mgr.set_tool_policy_provider(
        lambda: {"srv": {"disabled": {"x"}, "allowed": {"x"}}}
    )
    res = _run(mgr.call_tool("mcp__srv__x", {}))
    assert "disabled by admin policy" in res["error"]


def test_policy_provider_exception_is_fail_open(monkeypatch):
    """A broken policy provider must not break tool dispatch (logged + allowed)."""
    mgr = McpManager()

    def _boom():
        raise RuntimeError("db down")

    mgr.set_tool_policy_provider(_boom)
    res = _run(mgr.call_tool("mcp__srv__tool", {}))
    # Reaches the session check rather than being blocked by the broken policy.
    assert "not connected" in res["error"]


def test_unrelated_server_not_affected():
    mgr = McpManager()
    mgr.set_tool_policy_provider(
        lambda: {"srv_a": {"disabled": {"x"}, "allowed": None}}
    )
    # Tool on a different server -> no policy entry -> passes to session check.
    res = _run(mgr.call_tool("mcp__srv_b__x", {}))
    assert "not connected" in res["error"]
