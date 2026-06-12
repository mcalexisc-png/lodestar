"""Tests for the lightweight agent-tool plugins (Step 8).

Each tool is a bundled in-process plugin; tests drive them through the loader.
"""

import asyncio
import json
import os
import sqlite3

import pytest

from src.plugins.loader import PluginLoader


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def loader():
    return PluginLoader(state_file=None)


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    # Point the tool path allowlist at tmp so confined tools can read it.
    import src.tool_execution as te

    monkeypatch.setattr(te, "_AGENT_WORKDIR", str(tmp_path), raising=False)
    # _tool_path_roots() reads settings + workdir; ensure tmp is allowed by
    # making it the workdir root the helpers fall back to.
    return tmp_path


# ── datetime (no capabilities) ───────────────────────────────────────────────

def test_datetime_current(loader):
    res = _run(loader.execute("datetime_tool", json.dumps({"tz": "UTC"}), {}))
    assert res["exit_code"] == 0
    assert res["timezone"] == "UTC"


def test_datetime_unknown_tz(loader):
    res = _run(loader.execute("datetime_tool", json.dumps({"tz": "Mars/Olympus"}), {}))
    assert res["exit_code"] == 1
    assert "unknown timezone" in res["error"]


def test_datetime_conversion(loader):
    res = _run(loader.execute(
        "datetime_tool",
        json.dumps({"tz": "Asia/Tokyo", "from_tz": "UTC", "time": "2026-01-01T00:00:00"}),
        {},
    ))
    assert res["exit_code"] == 0
    # Tokyo is UTC+9.
    assert "09:00:00" in res["output"]


# ── csv (fs) ─────────────────────────────────────────────────────────────────

def test_csv_read(loader, workdir):
    p = workdir / "data.csv"
    p.write_text("name,age\nAda,36\nGrace,40\n")
    res = _run(loader.execute("csv_read", json.dumps({"path": str(p)}), {}))
    assert res["exit_code"] == 0
    assert res["columns"] == ["name", "age"]
    assert res["row_count"] == 2
    assert res["preview"][0]["name"] == "Ada"


def test_csv_column_subset(loader, workdir):
    p = workdir / "d.csv"
    p.write_text("a,b,c\n1,2,3\n")
    res = _run(loader.execute("csv_read", json.dumps({"path": str(p), "columns": ["a", "c"]}), {}))
    assert res["exit_code"] == 0
    assert set(res["preview"][0].keys()) == {"a", "c"}


def test_csv_outside_allowlist_rejected(loader):
    res = _run(loader.execute("csv_read", json.dumps({"path": "/etc/passwd"}), {}))
    assert res["exit_code"] == 1


# ── sqlite (fs, read-only) ───────────────────────────────────────────────────

def test_sqlite_select(loader, workdir):
    db = workdir / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE items(id INTEGER, name TEXT)")
    conn.execute("INSERT INTO items VALUES (1, 'a'), (2, 'b')")
    conn.commit()
    conn.close()

    res = _run(loader.execute("sqlite_query", json.dumps({"db": str(db), "sql": "SELECT * FROM items ORDER BY id"}), {}))
    assert res["exit_code"] == 0
    assert res["row_count"] == 2
    assert res["rows"][0]["name"] == "a"


def test_sqlite_parameterized(loader, workdir):
    db = workdir / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE u(id INTEGER)")
    conn.execute("INSERT INTO u VALUES (1), (2), (3)")
    conn.commit()
    conn.close()
    res = _run(loader.execute(
        "sqlite_query",
        json.dumps({"db": str(db), "sql": "SELECT * FROM u WHERE id > ?", "params": [1]}),
        {},
    ))
    assert res["exit_code"] == 0
    assert res["row_count"] == 2


def test_sqlite_rejects_writes(loader, workdir):
    db = workdir / "t.db"
    sqlite3.connect(str(db)).close()
    for sql in ["DELETE FROM x", "DROP TABLE x", "INSERT INTO x VALUES (1)", "UPDATE x SET a=1"]:
        res = _run(loader.execute("sqlite_query", json.dumps({"db": str(db), "sql": sql}), {}))
        assert res["exit_code"] == 1, sql


def test_sqlite_rejects_multiple_statements(loader, workdir):
    db = workdir / "t.db"
    sqlite3.connect(str(db)).close()
    res = _run(loader.execute(
        "sqlite_query",
        json.dumps({"db": str(db), "sql": "SELECT 1; DROP TABLE x"}),
        {},
    ))
    assert res["exit_code"] == 1


# ── file_search (fs + shell) ─────────────────────────────────────────────────

def test_file_search_finds_match(loader, workdir):
    (workdir / "a.txt").write_text("alpha\nbeta\n")
    (workdir / "b.txt").write_text("gamma\n")
    res = _run(loader.execute("file_search", json.dumps({"pattern": "beta", "path": str(workdir)}), {}))
    assert res["exit_code"] == 0
    assert res["count"] >= 1
    assert "beta" in res["output"]


def test_file_search_requires_pattern(loader, workdir):
    res = _run(loader.execute("file_search", json.dumps({"path": str(workdir)}), {}))
    assert res["exit_code"] == 1


# ── git (fs + shell, read-only) ──────────────────────────────────────────────

def test_git_rejects_write_subcommands(loader):
    for cmd in ["commit", "push", "reset", "rm", "checkout"]:
        res = _run(loader.execute("git_tool", json.dumps({"command": cmd}), {}))
        assert res["exit_code"] == 1
        assert "not allowed" in res["error"]


# ── rss (net, optional dep) ──────────────────────────────────────────────────

def test_rss_requires_http_url(loader):
    res = _run(loader.execute("rss_read", json.dumps({"url": "ftp://x/feed"}), {}))
    assert res["exit_code"] == 1


def test_rss_handles_missing_feedparser(loader, monkeypatch):
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *a, **k):
        if name == "feedparser":
            raise ImportError("no feedparser")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    res = _run(loader.execute("rss_read", json.dumps({"url": "https://example.com/feed"}), {}))
    assert res["exit_code"] == 1
    assert "feedparser is not installed" in res["error"]
