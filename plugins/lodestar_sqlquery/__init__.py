"""Read-only SQLite query plugin (stdlib ``sqlite3``).

Runs a single parameterized SELECT against a SQLite database the user points
at (confined to the host path allowlist). The connection is opened read-only
(``mode=ro`` URI) and only SELECT/WITH statements are accepted, so it cannot
modify data. Declares fs.
"""

from src.plugins.manifest import Capability, PluginManifest

_MAX_ROWS = 200


def manifest() -> PluginManifest:
    return PluginManifest(
        name="sqlite_query",
        when_to_use="When the user wants to run a read-only SQL SELECT against a SQLite database file.",
        how='Pass JSON {"db": str, "sql": "SELECT ...", "params": [..] (optional)}.',
        tags=["sqlite", "sql", "data"],
        capabilities=[Capability.FS],
        handler="plugins.lodestar_sqlquery:run",
        parameters={
            "db": {"type": "string", "description": "Path to the SQLite .db file."},
            "sql": {"type": "string", "description": "A single SELECT/WITH statement."},
            "params": {"type": "array", "description": "Positional query parameters."},
        },
    )


def run(content: str, ctx: dict) -> dict:
    import json
    import sqlite3

    try:
        args = json.loads(content) if content.strip().startswith("{") else {}
    except (ValueError, TypeError):
        args = {}

    db_path = (args.get("db") or "").strip()
    sql = (args.get("sql") or "").strip()
    params = args.get("params") or []
    if not db_path or not sql:
        return {"error": "sqlite_query: 'db' and 'sql' are required.", "exit_code": 1}
    if not isinstance(params, (list, tuple)):
        return {"error": "sqlite_query: 'params' must be a list.", "exit_code": 1}

    if not _is_read_only(sql):
        return {"error": "sqlite_query: only a single SELECT/WITH statement is allowed.", "exit_code": 1}

    resolved = _confine(db_path)
    if resolved is None:
        return {"error": "sqlite_query: db path is outside the allowed roots.", "exit_code": 1}

    try:
        # Read-only URI connection: cannot write even if the SQL tried to.
        uri = f"file:{resolved}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(sql, tuple(params))
            rows = [dict(r) for r in cur.fetchmany(_MAX_ROWS)]
        finally:
            conn.close()
    except sqlite3.Error as e:
        return {"error": f"sqlite_query: {e}", "exit_code": 1}

    return {
        "rows": rows,
        "row_count": len(rows),
        "truncated": len(rows) >= _MAX_ROWS,
        "output": f"{len(rows)} row(s)" + (" (truncated)" if len(rows) >= _MAX_ROWS else ""),
        "exit_code": 0,
    }


def _is_read_only(sql: str) -> bool:
    import re

    stripped = sql.strip().rstrip(";")
    # Reject multiple statements.
    if ";" in stripped:
        return False
    head = stripped.lstrip("(").lower()
    return bool(re.match(r"^(select|with)\b", head))


def _confine(db_path: str):
    try:
        from src.tool_execution import _resolve_tool_path

        return _resolve_tool_path(db_path)
    except Exception:
        return None
