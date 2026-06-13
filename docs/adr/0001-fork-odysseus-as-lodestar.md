# 0001 - Fork Odysseus as Lodestar

## Status

Accepted

## Context

[Odysseus](https://github.com/pewdiepie-archdaemon/odysseus), created by
PewDiePie (Felix Kjellberg), is a self-hosted AI workspace: FastAPI backend,
vanilla JS/CSS frontend, SQLite storage, local-first and privacy-first with
no telemetry. Lodestar starts from that codebase and continues it under a
new name and identity.

## Decision

- Rebrand the project as **Lodestar** (`lodestar` / `LODESTAR` for
  identifiers and env-var prefixes), with the tagline "Self-hosted AI for
  everyone — your own private workspace, guided by your own star, running on
  the hardware you already have."
- Preserve the architecture, local-first/privacy-first/no-telemetry
  posture, and vanilla JS/CSS frontend as-is.
- Preserve attribution: the LICENSE copyright line for the original author
  and all links to the upstream repository in credits/acknowledgments
  continue to point at the original project.
- Never rename third-party projects or packages Lodestar depends on or
  interoperates with (opencode, llmfit, Tongyi DeepResearch, ChromaDB,
  fastembed, SearXNG, ntfy, Ollama, vLLM, llama.cpp, Playwright, MCP, and
  their pip/npm package names) — only the project's own identifiers are
  renamed.
- Phase 1 of the fork is rebrand + cleanup + light scaffolding only. No new
  features. Anything beyond that scope is marked `# TODO(lodestar):` for a
  later phase.

## Consequences

- Environment variables previously prefixed `ODYSSEUS_*` are dual-read via
  `src/env_compat.py`: `LODESTAR_*` is checked first, with a
  `DeprecationWarning`-emitting fallback to the old `ODYSSEUS_*` name. The
  fallback can be removed once downstream configs have migrated.
- The `scripts/odysseus*` CLI dispatcher and subcommands are now
  `scripts/lodestar*`.
- A few identifiers with a larger blast radius — the `ody_` API token
  prefix and the `odysseus_kind`/`odysseus_ref` columns on the
  `scheduled_emails` table — were deliberately left unchanged in Phase 1
  (see the `# TODO(lodestar)` markers at their definitions) since renaming
  them needs a data migration, not just a text rename.
