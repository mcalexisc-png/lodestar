# 0002 - "opencode" is an LLM provider, not a Node/npx runtime dependency

## Status

Accepted

## Context

The README describes the Agent as "built on
[opencode](https://github.com/anomalyco/opencode)" (see
`ACKNOWLEDGMENTS.md`), and Phase 2's low-end-hardware push needed to confirm
whether that implies a Node.js/npx runtime dependency for core agent
features — a hidden cost for low-end users who may not have Node installed.

A grep across `src/`, `routes/`, and `static/js/` for "opencode" turns up
only:

- `src/llm_core.py` (`_detect_provider`, `_provider_label`) — recognizes
  `opencode.ai/zen` and `opencode.ai/zen/go` as LLM endpoint hostnames
  ("OpenCode Zen" / "OpenCode Go").
- `routes/webhook_routes.py` — preset base URLs for the same two endpoints
  (`https://opencode.ai/zen/v1`, `https://opencode.ai/zen/go/v1`).
- `static/js/slashCommands.js`, `static/js/providers.js` — provider picker
  entries (name, logo, base URL) for the same two endpoints.
- `src/copilot.py` — a comment noting the GitHub Copilot token-exchange flow
  "mirrors how editors / opencode talk to Copilot" (a design reference, not
  a dependency).
- `ACKNOWLEDGMENTS.md` — credits the
  [opencode](https://github.com/anomalyco/opencode) project (MIT) as the
  source the agent-loop / tool-execution design was adapted from.

None of these touch `subprocess`, `node`, or `npx`. "opencode" in this
codebase means exactly two things, both unrelated to a runtime dependency:

1. **An OpenAI-compatible LLM endpoint provider** (OpenCode Zen / Go) that a
   user can optionally select in Settings, like Groq or OpenRouter.
2. **A design-pattern credit** — the agent loop's architecture was adapted
   from the upstream opencode project's source, per
   `ACKNOWLEDGMENTS.md`.

The actual Node/npx dependency in this codebase is unrelated to "opencode"
by name: it's the **built-in Playwright browser MCP server**
(`src/builtin_mcp.py`, `_BUILTIN_NPX_SERVERS["builtin_browser"]`), which
shells out to `npx -y @playwright/mcp@latest` to provide page
navigation/screenshot/vision tools.

## Decision

- Document that "opencode" is an LLM provider option + a design-pattern
  credit — **not** a Node/npx runtime requirement. Core chat, agent
  (without the browser tool), memory, documents, email, calendar, and deep
  research all run on Python alone.
- The Playwright/browser MCP is the only Node/npx-touching code path. It is
  already handled defensively, independent of this ADR:
  - `src/builtin_mcp.py::register_builtin_servers` skips registering it
    entirely when `LODESTAR_LITE=true` (Phase 2 Step 4).
  - In full mode, it only starts if `@playwright/mcp` is already present in
    the local npx cache; otherwise it logs a clear skip message
    ("this server is optional; see README.md...") and the rest of the app
    continues normally.
  - `_find_npx()` falls back through several common install paths so a
    `node`/`npx` on PATH is found even outside a login shell, but its
    absence is not fatal.
- README's "Built-in MCP servers (optional setup)" section (already present)
  correctly frames Node/npx as optional, scoped to the browser MCP. No
  wording change needed.

## Verification

Booted the app (`LODESTAR_LITE=false`, full mode) with `npx`/`node` hidden
from `PATH` in a throwaway shell. Result: clean startup (HTTP 200/302 on
`/`), all non-browser built-in MCP servers (Memory, Email, Image Generation,
RAG) registered normally, and the Browser MCP logged its existing
"not available... this server is optional" message without affecting
anything else. No code changes were required — the existing degrade-gracefully
path (Step 4) already covers this.

## Consequences

- No action needed beyond this ADR: the coupling some users might infer from
  "built on opencode" does not exist as a runtime dependency.
- If a future feature *does* introduce a real Node/npx dependency for core
  (non-browser) functionality, it must follow the same pattern as
  `_BUILTIN_NPX_SERVERS`: optional, lazily detected, and gated behind
  `LODESTAR_LITE` if it adds meaningful startup cost on low-end hardware.
