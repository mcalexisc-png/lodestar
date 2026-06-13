# Security Policy

Lodestar is a self-hosted AI workspace with privileged local capabilities. Please do not run it as a public, unauthenticated service.

## Supported Versions

Security fixes are handled on the default branch until formal releases are cut.

## Deployment Guidance

- Keep `AUTH_ENABLED=true` for any network-accessible deployment.
- Keep `LOCALHOST_BYPASS=false` outside local development.
- Set `SECURE_COOKIES=true` when Lodestar is served through HTTPS by a trusted reverse proxy or private access gateway.
- Use HTTPS when exposing the app beyond localhost.
- Put the authenticated Lodestar web/API entrypoint behind a trusted reverse proxy or private access layer such as Cloudflare Access, Tailscale, or a VPN.
- Keep ChromaDB, SearXNG, ntfy, Ollama, vLLM, llama.cpp, databases, and raw model/provider APIs internal-only.
- Protect `.env`, `data/`, `logs/`, uploads, generated media, backups, auth/session files, database files, API keys, and model/provider tokens.
- Disable open signup unless you intentionally want new accounts.
- Keep demo/test users non-admin, and remove them entirely on serious deployments.
- Give admin accounts strong passwords and enable 2FA where possible.
- Leave high-risk agent tools restricted to admins: shell, Python, file read/write, email send/read, MCP, app API, task/skill/memory management, settings, tokens, and model serving.
- Rotate API keys, webhook secrets, and Lodestar API tokens if they appear in logs, screenshots, demos, or shared chats.
- Treat shell, model-serving, MCP, email, calendar, and vault features as privileged admin functionality.
- Common internal-only ports are Lodestar `7000`, SearXNG `8080`, ntfy `8091`, ChromaDB `8100`, Ollama `11434`, and local model/provider APIs such as `8000-8020`.

### Lite mode

Lite mode (`LODESTAR_LITE=true`) reduces the attack surface by disabling
ChromaDB, the Playwright browser MCP server, and reducing SQLite cache sizes.
For memory-constrained or security-conscious single-user deployments, lite
mode is the recommended default. Semantic search degrades to keyword search
but all other features remain functional.

### Plugin system

In-process plugins (Tier 2) run inside the app process with no sandbox
boundary. Capability enforcement (`net`, `fs`, `shell`) is best-effort for
trusted code. For untrusted or third-party extensions, use MCP servers
(Tier 1) which run as separate processes. See `docs/plugin-authoring.md`.

### Agent tools

Non-admin users are blocked from all high-risk tools (shell, Python, file
read/write, email, MCP, model serving, vault, settings). Admins have full
access by design. There is no per-tool approval gate — a prompt-injection
reaching an admin session can execute arbitrary commands. Treat admin sessions
as you would a root shell.

## Publishing A Fork

Before pushing a public fork, run:

```bash
git status --short
git check-ignore -v .env data/auth.json data/app.db logs/compound.log
git grep -n -I -E "(sk-[A-Za-z0-9_-]{20,}|xox[baprs]-|AIza[0-9A-Za-z_-]{20,}|Bearer [A-Za-z0-9._~+/-]{20,})" -- . ':!static/lib/**' ':!package-lock.json'
```

Only `.env.example`, docs, source, tests, and static assets should be committed. Never commit live `.env` values, `data/` contents, local databases, uploaded files, generated media, logs, backups, auth/session files, API keys, model/provider tokens, password hashes, or personal documents.

## Reporting

Please report vulnerabilities privately via GitHub security advisories if available, or by opening a minimal issue that does not disclose exploit details.
