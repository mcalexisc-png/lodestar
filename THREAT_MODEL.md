# Threat Model

Lodestar is a **self-hosted AI workspace with privileged local access**. This document states the trust boundary so contributors can reason about security decisions without reading through the full auth and middleware stack.

## Trust Boundary

Lodestar is designed for **trusted users on a private network**, not public exposure. The README describes it as "treat it like an admin console" — that framing is accurate. A logged-in admin can execute shell commands, read and write files, send email, and control model serving. This is intentional. The threat model does not try to prevent admins from doing these things. It does try to prevent:

- Unauthenticated access
- Non-admins reaching admin-only capabilities
- The AI agent acting on instructions injected through untrusted content (web results, emails, fetched pages, memories)
- Internal services (ChromaDB, Ollama, SearXNG, etc.) being reachable from outside the host

## Roles and Capabilities

| Capability | Admin | Non-admin (default) |
|---|---|---|
| Chat with agent | ✓ | ✓ |
| Browser tool | ✓ | ✓ |
| Documents | ✓ | ✓ |
| Research mode | ✓ | ✓ |
| Image generation | ✓ | ✓ |
| Memory management | ✓ | ✓ |
| Shell / Python execution | ✓ | ✗ |
| File read / write | ✓ | ✗ |
| Email send / read | ✓ | ✗ |
| MCP tools | ✓ | ✗ |
| Calendar management | ✓ | ✗ |
| Token / webhook management | ✓ | ✗ |
| Model serving | ✓ | ✗ |
| Vault | ✓ | ✗ |
| Settings | ✓ | ✗ |
| UI panel control | ✓ | ✓ |

Non-admin defaults are in `core/auth.py:DEFAULT_PRIVILEGES`. Tool enforcement is in `src/tool_security.py:NON_ADMIN_BLOCKED_TOOLS`. Any tool whose name starts with `mcp__` is also blocked for non-admins. Admins always get full access regardless of stored privilege values.

## Authentication

- **Sessions:** bcrypt passwords, 7-day session tokens stored atomically in `data/sessions.json` via `core/atomic_io.py`.
- **2FA:** TOTP with 8 single-use backup codes. Verified after password check, before session issuance.
- **Reserved usernames:** `internal-tool`, `api`, `demo`, `system` cannot be registered or renamed into. Defined in `core/auth.py:RESERVED_USERNAMES`.
  - `internal-tool` is security-critical: `core/middleware.py:require_admin` treats any request where `request.state.current_user == "internal-tool"` as the in-process tool loopback and grants admin unconditionally. A real account with that name would silently pass every `require_admin` check.
- **Orphan sessions:** `validate_token` re-checks that the user record still exists on every call. A deleted user's cookie is dropped on next request rather than continuing to authenticate.

## Internal Tool Loopback

Agent tool calls reach admin-gated HTTP routes over an in-process HTTP loopback. The mechanism:

1. At app startup, `core/middleware.py` generates a random `INTERNAL_TOOL_TOKEN` via `secrets.token_hex(32)`. It is never persisted and never sent to clients.
2. Loopback requests carry `X-Lodestar-Internal-Token: <token>` or have `request.state.current_user` already set to `"internal-tool"` by the auth middleware.
3. `require_admin` recognises either signal and grants access without checking the session user.

The agent may be running in a non-admin user's session, but tool dispatch first calls `src/tool_security.py:owner_is_admin_or_single_user` to verify the session owner is an admin before issuing any loopback call. Non-admin users cannot invoke admin tools even via the agent.

## Prompt-Injection Hardening

External content that reaches the LLM is treated as untrusted via `src/prompt_security.py`:

- `untrusted_context_message(label, content)` wraps the content in a `user`-role message with a header block instructing the model not to follow instructions inside it. Content goes in as data, not as a system instruction.
- `UNTRUSTED_CONTEXT_POLICY` is a system-prompt preamble that states the same policy at the top of every session where untrusted data may appear.

**Untrusted surfaces that must go through this wrapper:** web search results, fetched URLs, emails (read), saved memories, skill text, notes, and any tool output sourced from outside the server. Injecting untrusted content directly into the system role is a security bug.

## Security Headers

`core/middleware.py:SecurityHeadersMiddleware` sets headers on every response:

- `X-Frame-Options: DENY` + `frame-ancestors 'none'` on all routes except tool-render iframes (which are sandboxed at the HTML level).
- `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer` everywhere.
- **CSP:** nonce-based `script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net`. `style-src 'unsafe-inline'` is intentionally kept — `static/index.html` ships inline `<style>` blocks and JS modules set `style=""` attributes at runtime. Inline styles do not execute script so the risk is visual-only. Removing this requires templating the HTML files and auditing all JS-set style attributes.

## Plugin System (Phases 2–4)

### In-process plugins (Tier 2)

- Plugins declare capabilities (`net`, `fs`, `shell`) in their manifest.
- Capability enforcement is best-effort: the host checks `require_capability()` calls, but a plugin that ignores the check is not blocked by the OS.
- Plugins run as the app process user with full network and filesystem access.
- Plugin handlers are lazy-imported on first use; unused plugins cost nothing at startup.
- Plugin UI panels use a fixed widget vocabulary (no arbitrary JS injection) or sandboxed iframes (no `allow-same-origin`).

### MCP servers (Tier 1)

- Out-of-process, language-agnostic, speak the Model Context Protocol.
- Per-server tool allowlists and denylists enforced at the execution boundary (not just hidden from the model).
- Non-admin users are blocked from all `mcp__*` tools.
- Third-party MCP servers can supply malicious tool schemas; schema sanitization caps token sizes but does not eliminate schema-based prompt injection.

### Tool policy layers

1. **User-disabled tools** — per-server `disabled_tools` / `allowed_tools` in DB.
2. **Plan mode** — read-only allowlist; known mutators denied.
3. **Guide-only mode** — all tools blocked (heuristic detection).
4. **Admin gating** — `NON_ADMIN_BLOCKED_TOOLS` set (40+ tools) + `mcp__*` blanket block for non-admins.

## Embedded Vector Store (sqlite-vec)

- Stores embeddings in `data/vectors.db` (separate from `app.db`).
- No network service — fully embedded, single-process.
- The `vec0` SQLite extension is loaded via `conn.enable_load_extension(True)` then immediately disabled. Supply-chain risk if the extension binary is tampered with.
- Memory text lives in `memory.json`; the vector store is a rebuildable index.
- No encryption at rest (same as `data/app.db`).

## Known Gaps

These are open, acknowledged, and contributor help is welcome:

1. **No shell/filesystem sandbox.** The agent `bash` and `read_file`/`write_file` tools run as the app process user with no network egress filtering or filesystem confinement. A successful prompt-injection reaching a shell-enabled admin session can make outbound requests to internal services. See #1058 for the sandbox proposal.

2. **SSRF via `/api/v1/chat` `base_url` parameter.** A chat-scoped API token can supply an arbitrary `base_url`; the server forwards the LLM request to that host without validating the scheme or address. PR #1039 fixes this.

3. **`src/search/` partial consolidation.** `src.search.core` and `src.search.providers` correctly alias `services.search` via `sys.modules` replacement. `analytics`, `cache`, `content`, `query`, and `ranking` are still independent copies that can drift. The SSRF regression tests in `tests/test_webhook_ssrf_resilience.py` test `src.webhook_manager` directly (separate from search), so the safety net there is intact. See #1058.

4. **Token scopes are coarse.** There is no way to grant a session a subset of the owning user's privileges. Companion/mobile tokens carry either `chat` or `admin` scope with no per-capability granularity.

5. **No per-tool approval gate.** Admins can execute high-risk tools (shell, file write, email send) without explicit confirmation. A prompt-injection in an admin session can run arbitrary commands. There is no "require user approval before executing this specific tool" mechanism.

6. **Model endpoint API keys stored in plaintext SQLite.** The `ModelEndpoint` table stores `api_key` as plaintext, unlike email credentials which use Fernet encryption. A local file read of `data/app.db` exposes LLM API keys.

7. **MCP schema injection.** Third-party MCP servers supply tool schemas that are rendered into the LLM prompt. Schema sanitization caps token sizes but a malicious server can still craft schemas that influence model behavior.

8. **Incomplete executable upload blocklist.** The upload handler blocks common executable extensions (`.exe`, `.dll`, `.bat`, `.cmd`, `.vbs`, `.ps1`) but does not block `.scr`, `.com`, `.pif`, or other less common formats. No antivirus/malware scanning.

9. **No CSRF tokens.** Relies on `SameSite=Lax` cookies for CSRF protection. Generally sufficient for cookie-based auth but does not protect against subdomain attacks.

10. **sqlite-vec extension supply chain.** The `vec0` SQLite extension is loaded from the Python package. A tampered extension binary could execute arbitrary code during load.
