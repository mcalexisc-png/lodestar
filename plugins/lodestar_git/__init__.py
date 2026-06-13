"""Git plugin: shell out to ``git`` for read-oriented repo inspection.

Supports status / log / diff / show / branch. Write operations (commit, push,
reset, ...) are rejected — this tool is for inspection. Declares fs + shell.
The repo directory is confined to the host path allowlist.
"""

from src.plugins.manifest import Capability, PluginManifest

_ALLOWED_SUBCOMMANDS = {"status", "log", "diff", "show", "branch", "remote", "tag"}


def manifest() -> PluginManifest:
    return PluginManifest(
        name="git_tool",
        when_to_use="When the user wants to inspect a git repo: status, log, diff, branches.",
        how='Pass JSON {"command": str (e.g. "status"), "args": [str], "repo": str (optional)}.',
        tags=["git", "vcs", "dev"],
        capabilities=[Capability.FS, Capability.SHELL],
        handler="plugins.lodestar_git:run",
        parameters={
            "command": {"type": "string", "description": "git subcommand (status/log/diff/show/branch)."},
            "args": {"type": "array", "items": {"type": "string"}, "description": "Extra args."},
            "repo": {"type": "string", "description": "Repo directory (default: workspace)."},
        },
    )


def run(content: str, ctx: dict) -> dict:
    import json
    import shutil
    import subprocess

    try:
        args = json.loads(content) if content.strip().startswith("{") else {"command": content.strip()}
    except (ValueError, TypeError):
        args = {"command": content.strip()}

    subcommand = (args.get("command") or "status").strip().split()[0] if (args.get("command") or "").strip() else "status"
    if subcommand not in _ALLOWED_SUBCOMMANDS:
        return {
            "error": f"git_tool: '{subcommand}' is not allowed. "
                     f"Read-only subcommands only: {sorted(_ALLOWED_SUBCOMMANDS)}.",
            "exit_code": 1,
        }

    if not shutil.which("git"):
        return {"error": "git_tool: git is not installed.", "exit_code": 1}

    repo = _confine(args.get("repo"))
    if repo is None:
        return {"error": "git_tool: repo path is outside the allowed roots.", "exit_code": 1}

    extra = [str(a) for a in (args.get("args") or [])]
    cmd = ["git", "-C", repo, subcommand, *extra]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as e:
        return {"error": f"git_tool: {e}", "exit_code": 1}

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    return {
        "output": out or err or "(no output)",
        "exit_code": proc.returncode,
    }


def _confine(repo):
    import os

    try:
        from src.tool_execution import _AGENT_WORKDIR, _resolve_tool_path
    except Exception:
        return None
    candidate = (repo or "").strip() or _AGENT_WORKDIR
    try:
        return _resolve_tool_path(candidate)
    except Exception:
        return None
