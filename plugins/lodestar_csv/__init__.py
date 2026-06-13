"""CSV / tabular plugin using the stdlib ``csv`` module (no pandas).

Reads a CSV file (confined to the host path allowlist) and returns a small
summary plus optional row preview / column selection. For typical config /
export sizes; not a dataframe engine.
"""

from src.plugins.manifest import Capability, PluginManifest


def manifest() -> PluginManifest:
    return PluginManifest(
        name="csv_read",
        when_to_use="When the user wants to inspect, preview, or summarize a CSV/tabular file.",
        how='Pass JSON {"path": str, "limit": int (optional), "columns": [str] (optional)}.',
        tags=["csv", "data", "tabular"],
        capabilities=[Capability.FS],
        handler="plugins.lodestar_csv:run",
        parameters={
            "path": {"type": "string", "description": "Path to the CSV file."},
            "limit": {"type": "integer", "description": "Max rows to preview (default 20)."},
            "columns": {"type": "array", "items": {"type": "string"},
                        "description": "Subset of columns to return."},
        },
    )


def run(content: str, ctx: dict) -> dict:
    import csv
    import json

    try:
        args = json.loads(content) if content.strip().startswith("{") else {"path": content.strip()}
    except (ValueError, TypeError):
        args = {"path": content.strip()}

    path = (args.get("path") or "").strip()
    if not path:
        return {"error": "csv_read: 'path' is required.", "exit_code": 1}

    resolved = _confine(path)
    if resolved is None:
        return {"error": "csv_read: path is outside the allowed roots.", "exit_code": 1}

    limit = int(args.get("limit") or 20)
    want_cols = args.get("columns") or None

    try:
        with open(resolved, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            rows = []
            total = 0
            for row in reader:
                total += 1
                if len(rows) < limit:
                    if want_cols:
                        row = {c: row.get(c, "") for c in want_cols}
                    rows.append(row)
    except FileNotFoundError:
        return {"error": f"csv_read: file not found: {path}", "exit_code": 1}
    except Exception as e:
        return {"error": f"csv_read: {e}", "exit_code": 1}

    return {
        "columns": headers,
        "row_count": total,
        "preview": rows,
        "output": f"{total} rows, {len(headers)} columns: {', '.join(headers)}",
        "exit_code": 0,
    }


def _confine(path: str):
    try:
        from src.tool_execution import _resolve_tool_path

        return _resolve_tool_path(path)
    except Exception:
        return None
