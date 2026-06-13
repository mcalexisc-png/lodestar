"""File search plugin: ripgrep with a stdlib fallback.

Searches text files under an allowed root for a pattern. Prefers ``rg``
(ripgrep) for speed; falls back to a stdlib ``os.walk`` + ``re`` scan if rg is
not installed. Declares fs + shell capabilities. Paths are confined to the
host's tool path allowlist (same deny/allow rules as the file tools).
"""

from src.plugins.manifest import Capability, PluginManifest


def manifest() -> PluginManifest:
    return PluginManifest(
        name="file_search",
        when_to_use="When the user wants to find files or lines matching text/a pattern under a directory.",
        how='Pass JSON {"pattern": str, "path": str (optional), "max_results": int (optional)}.',
        tags=["files", "search", "ripgrep"],
        capabilities=[Capability.FS, Capability.SHELL],
        handler="plugins.lodestar_filesearch:run",
        parameters={
            "pattern": {"type": "string", "description": "Text or regex to search for."},
            "path": {"type": "string", "description": "Directory to search (default: workspace)."},
            "max_results": {"type": "integer", "description": "Max matching lines (default 100)."},
        },
    )


def run(content: str, ctx: dict) -> dict:
    import json
    import os
    import re
    import shutil
    import subprocess

    try:
        args = json.loads(content) if content.strip().startswith("{") else {"pattern": content.strip()}
    except (ValueError, TypeError):
        args = {"pattern": content.strip()}

    pattern = (args.get("pattern") or "").strip()
    if not pattern:
        return {"error": "file_search: 'pattern' is required.", "exit_code": 1}
    max_results = int(args.get("max_results") or 100)

    # Confine the search root to the host's allowlist.
    raw_path = (args.get("path") or "").strip()
    root = _resolve_root(raw_path)
    if root is None:
        return {"error": "file_search: path is outside the allowed roots.", "exit_code": 1}

    rg = shutil.which("rg")
    if rg:
        try:
            proc = subprocess.run(
                [rg, "--line-number", "--no-heading", "--color", "never",
                 "--max-count", str(max_results), pattern, root],
                capture_output=True, text=True, timeout=30,
            )
            lines = [ln for ln in proc.stdout.splitlines() if ln][:max_results]
            return {"output": "\n".join(lines) or "(no matches)", "count": len(lines),
                    "engine": "ripgrep", "exit_code": 0}
        except Exception:
            pass  # fall through to stdlib

    # stdlib fallback
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return {"error": f"file_search: invalid pattern: {e}", "exit_code": 1}
    matches = []
    for dirpath, _dirs, files in os.walk(root):
        for fname in files:
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for n, line in enumerate(f, 1):
                        if rx.search(line):
                            matches.append(f"{fpath}:{n}:{line.rstrip()}")
                            if len(matches) >= max_results:
                                return {"output": "\n".join(matches), "count": len(matches),
                                        "engine": "stdlib", "exit_code": 0}
            except (OSError, UnicodeDecodeError):
                continue
    return {"output": "\n".join(matches) or "(no matches)", "count": len(matches),
            "engine": "stdlib", "exit_code": 0}


def _resolve_root(raw_path: str):
    """Resolve and confine the search root using the host path allowlist."""
    import os

    try:
        from src.tool_execution import _resolve_tool_path, _AGENT_WORKDIR
    except Exception:
        _resolve_tool_path = None
        _AGENT_WORKDIR = os.getcwd()

    candidate = raw_path or _AGENT_WORKDIR
    if _resolve_tool_path is not None:
        try:
            resolved = _resolve_tool_path(candidate)
            return resolved if resolved else None
        except Exception:
            return None
    # No confinement helper available: only allow the workspace.
    return _AGENT_WORKDIR if not raw_path else None
