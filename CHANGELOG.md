# Changelog

All notable changes to Lodestar are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

## [0.1.0] — 2026-06-13

First release of Lodestar, a fork of
[Odysseus](https://github.com/pewdiepie-archdaemon/odysseus) by PewDiePie
(Felix Kjellberg). See [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md) and
[NOTICE](NOTICE) for upstream credit.

### Added

**Low-end hardware focus (Phases 2–3)**
- Lite mode (`LODESTAR_LITE=true`) for machines with limited RAM/CPU and no GPU
- `install-lite.sh` / `install-lite.ps1` — one-command lite installers
- Keyword-search fallback when ChromaDB/fastembed are unavailable
- Reduced SQLite cache/mmap sizes in lite mode
- Single uvicorn worker in lite mode

**Embedded vector store (Phase 2)**
- SQLite-vec backend for vector memory (embedded, no server needed)
- `LODESTAR_VECTOR_BACKEND` env var: `auto`, `sqlite_vec`, `chromadb`
- Fingerprint-based model swap detection and automatic index rebuild
- Backward-compatible: ChromaDB still supported for multi-user setups

**Plugin system (Phase 2)**
- Two-tier plugin architecture: MCP servers (Tier 1) + in-process plugins (Tier 2)
- Four-field plugin manifest (`name`, `when_to_use`, `how`, `tags`)
- Capability enforcement (`net`, `fs`, `shell`) for in-process plugins
- Lazy handler import — unused plugins cost nothing at startup
- 7 bundled plugins: text_stats, file_search, csv_read, datetime_tool, git_tool, sqlite_query, rss_read
- Plugin UI panels with schema widgets and sandboxed iframes
- `lodestar.tools` entry point for third-party pip-installable plugins

**New features (Phase 3)**
- Deep Research — multi-step research with visual reports and citations
- Compare — blind side-by-side model comparison
- Notes & Tasks — persistent notes with reminders, todo list, cron-style scheduled tasks
- Calendar — CalDAV sync with Radicale, Nextcloud, Apple, Fastmail
- Email triage — urgency scoring, auto-tagging, auto-summary, auto-reply drafts
- Cookbook improvements — hardware scan, VRAM-aware model scoring, one-click download/serve
- Code workspace — in-browser code editing and execution
- Image editor — gallery with inpainting and transform tools
- TTS (text-to-speech) — AI-generated audio responses
- Vault — encrypted secret storage
- Companion pairing — mobile/companion device authentication
- Codex and Claude integration routes

**Optimizations (Phase 4)**
- Deferred heavy module loading from import time to lifespan
- Async `_resolve_model` with `httpx.AsyncClient` (no sync blocking in request path)
- SQLite-vec cache-layer optimizations
- Frontend: async CSS loading, deferred route modules, PWA icons
- Cold start reduced from 4.5s to 3.5s (full mode)
- Idle RSS: 186 MB (lite), 364 MB (full)

**Documentation (Phase 5)**
- `docs/install.md` — every install path: Docker, native, lite, Windows, macOS
- `docs/usage.md` — feature guide for all shipped features
- `docs/configuration.md` — full env-var reference with legacy `ODYSSEUS_*` aliases
- `docs/benchmarks.md` — reproducible benchmark results with method
- `docs/plugin-authoring.md` — MCP + in-process plugin authoring guide
- `docs/media-checklist.md` — screenshot and video capture checklist
- `docs/branding-assets.md` — logo, favicon, social card specs
- Updated SECURITY.md and THREAT_MODEL.md for fork's attack surface
- 4 architecture decision records (fork, opencode/Node, sqlite-vec, MCP allowlist)

**Security**
- Admin-gated tool enforcement for shell, Python, file I/O, email, MCP, model serving
- Per-server MCP tool allowlists and denylists
- Non-admin users blocked from all `mcp__*` tools
- Plan mode with read-only tool allowlist
- Guide-only mode disables all tools
- Path confinement for read_file/write_file (symlink-resolved)
- Upload handler with dangerous file type blocking, rate limiting, owner-scoped access
- `X-Content-Type-Options: nosniff` on all responses

### Changed
- Renamed from Odysseus to Lodestar across all user-facing surfaces
- Legacy `ODYSSEUS_*` env vars retained as deprecated aliases with startup warning
- `LODESTAR_DATA_DIR` replaces `ODYSSEUS_DATA_DIR` as the primary env var
- Frontend localStorage migration map handles `odysseus-*` → `lodestar-*` keys

### Known limitations (v0.1.0)
- No shell/filesystem sandbox for agent tools
- No per-tool approval gate for admins
- Model endpoint API keys stored in plaintext SQLite
- Cookie name still `odysseus_session` (changing would invalidate sessions)
- DB columns `odysseus_kind`/`odysseus_ref` not yet renamed (data migration needed)
- ChromaDB collection names (`odysseus_memories`, `odysseus_rag`) not yet renamed
- No CSRF tokens (relies on SameSite=Lax)
- Cold start still above 3s target

[0.1.0]: https://github.com/mcalexisc-png/lodestar/releases/tag/v0.1.0
