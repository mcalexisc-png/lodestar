# 0004 - MCP-first extensions with per-tool allow/deny enforcement

## Status

Accepted

## Context

Lodestar's primary extension mechanism is **MCP servers** (out-of-process,
language-agnostic) — the right place for anything heavy, third-party, or
untrusted, because a misbehaving plugin can't OOM or crash the host app. The
infrastructure already exists: `McpManager` connects stdio/SSE/HTTP servers,
built-in servers auto-register at startup, npx-based servers only start when
already cached (so a fresh install never blocks on a multi-minute download),
and all MCP *management* routes are admin-gated.

The gap was **per-tool access control**. A `disabled_tools` denylist existed,
but it only *hid* tools from the LLM prompt/schemas — it was not enforced at the
execution boundary, so a hallucinated or stale qualified tool name
(`mcp__server__tool`) could still be dispatched. And there was no *allowlist* —
the "low-end users enable only what they need" control the planning doc calls
for.

## Decision

- Add a per-server **allowlist** (`allowed_tools` column on `mcp_servers`)
  alongside the existing **denylist** (`disabled_tools`). When `allowed_tools`
  is set, only those tools may run; `NULL` means no allowlist. `disabled_tools`
  always wins.
- Enforce both at the **execution boundary**: `McpManager.call_tool` consults an
  injected tool-policy provider and rejects a blocked/non-allowlisted tool
  before reaching the server session. The provider is installed by the routes
  layer (which owns the DB) via `set_tool_policy_provider`, keeping the manager
  DB-decoupled and easy to unit-test. A broken provider fails open (logged) so
  policy errors never break tool dispatch.
- Also fold the allowlist into the prompt/schema **hiding** path
  (`_load_mcp_disabled_map`), so non-allowlisted tools are both hidden from the
  LLM and rejected at runtime (defense in depth).
- Manage the allowlist via an admin-gated route
  (`PATCH /api/mcp/servers/{id}/allowlist`), mirroring the existing
  `disabled_tools` endpoint.

## Consequences

- The allow/deny lists are now a real security control, not just a prompt-shaping
  hint. Low-end operators can pin a server down to exactly the tools they want.
- No change to the cached-npx startup behavior or the admin gating model — this
  builds on them.
- Built-in and third-party MCP servers continue to register through the same
  path; the allowlist applies uniformly by `server_id`.
- Rule of thumb (published in plugin-authoring docs): *anything heavy,
  third-party, or untrusted → ship it as an MCP server; reserve in-process
  plugins for small, trusted, pure-Python tools.*
