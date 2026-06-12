# Plugin Authoring Guide

Lodestar has a **two-tier plugin system**. Choose the right tier:

> **Rule of thumb:** anything heavy, third-party, or untrusted → ship it as an
> **MCP server** (Tier 1, out-of-process). Reserve **in-process plugins**
> (Tier 2) for small, trusted, pure-Python tools.

This is a hard isolation boundary, not a style preference: an in-process plugin
runs inside the app process, so a leak or crash affects the host (which may have
only 4 GB of RAM). MCP servers run as separate processes and can't take the app
down.

---

## Tier 1 — MCP servers (recommended for most extensions)

MCP servers are language-agnostic processes that speak the Model Context
Protocol. Lodestar discovers, connects, and routes tools to them, and
management is admin-gated. See `src/mcp_manager.py` and `src/builtin_mcp.py`.

Key behaviors to rely on:

- **Cached-npx startup**: npx-based servers only start when their package is
  already cached, so a fresh install never blocks on a multi-minute download.
- **Per-tool allow/deny**: admins can set a denylist (`disabled_tools`) and an
  allowlist (`allowed_tools`) per server. Both are enforced at the execution
  boundary, not just hidden from the model (see ADR 0004). Manage via
  `PATCH /api/mcp/servers/{id}/allowlist` and
  `PATCH /api/mcp/servers/{id}/tools`.

Register an MCP server through the admin MCP UI / API like any other.

---

## Tier 2 — In-process plugins (small, trusted, pure-Python)

An in-process plugin is a tiny Python tool the agent can call directly.

### The four-field manifest

Every plugin ships a `PluginManifest` (see `src/plugins/manifest.py`):

| Field         | Meaning                                                        |
|---------------|----------------------------------------------------------------|
| `name`        | Unique tool name the agent calls (also the tool tag).          |
| `when_to_use` | One line telling the agent *when* to reach for this tool.      |
| `how`         | One line on how to call it (expected input).                   |
| `tags`        | Short tags for grouping/discovery.                             |

Plus:

- `capabilities`: a list of `Capability` (`net` / `fs` / `shell`) the plugin
  needs. The host enforces these — a plugin that didn't declare `net` is denied
  the network surface when it calls `ctx['require_capability']('net')`. (This
  is best-effort host enforcement for trusted tools; the strong boundary is
  still MCP.)
- `handler`: an `async (content, ctx) -> dict` callable, **or** a
  `"module:attr"` import path. If a string, it is **lazy-imported on first
  use** — installed-but-unused plugins cost nothing at startup beyond reading
  the manifest.
- `parameters` (optional): JSON-schema `properties` shown to the model;
  defaults to a single `input` string.

### Two ways to distribute

1. **Bundled (first-party):** add a package under the repo `plugins/` directory
   exposing a `manifest` attribute. Discovered automatically when the app runs
   from source — no pip install needed. See `plugins/lodestar_textstats/` for a
   complete example.

2. **Third-party (pip package):** declare a `lodestar.tools` entry point:

   ```toml
   [project.entry-points."lodestar.tools"]
   my_tool = "my_package.tool:manifest"
   ```

   Install with `lodestar plugins install <pip-requirement>`.

### The handler contract

```python
def run(content: str, ctx: dict) -> dict:
    # content: the JSON args string (or raw text) the agent passed.
    # ctx: {"owner", "session_id", "granted_capabilities", "require_capability"}.
    # Return a dict; {"output": "...", "exit_code": 0} on success,
    # {"error": "...", "exit_code": 1} on failure.
    ctx["require_capability"]("net")   # raises PermissionError if not declared
    ...
    return {"output": "...", "exit_code": 0}
```

Keep heavy imports **inside** the handler so discovery stays cheap.

### Example

`plugins/lodestar_textstats/__init__.py` is a complete, zero-capability example
(text statistics). Its `manifest()` is read at startup; its `run()` is imported
only when the `text_stats` tool is first called.

### Managing plugins

```
lodestar plugins list                 # discovered plugins + enabled state
lodestar plugins info <name>          # one plugin's manifest
lodestar plugins enable <name>        # enable (persisted to data/plugins.json)
lodestar plugins disable <name>       # disable
lodestar plugins install <src>        # pip-install a third-party plugin
```

Disabled plugins are neither offered to the model nor executable.
