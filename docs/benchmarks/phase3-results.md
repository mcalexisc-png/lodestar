# Phase 3 Results — defaults stay light

Phase 3 added new capabilities (embedded sqlite-vec memory, pluggable
embeddings, API search providers, a two-tier plugin system, plugin UI panels,
and lightweight agent tools). The acceptance bar: **every new feature is opt-in
or interface-selected, and the defaults must not regress the Phase-2 low-end
baseline.** This page records the verification.

## Phase-2 baseline (for reference)

From `docs/benchmarks/phase2-results.md`, same hardware (AMD Ryzen 7 3750H,
~5.9 GB RAM, Linux, Python 3.14), uvicorn boot, idle `VmRSS`:

| Mode | Cold start | Idle RSS |
|---|---|---|
| Full (`LODESTAR_LITE=false`) | ~3.5s | ~212 MB |
| Lite (`LODESTAR_LITE=true`)  | ~3.0s | ~189 MB |

`pytest -m "not slow"`: 3205 passed, 3 pre-existing failures (path-with-spaces
in `tests/test_run_focus.py`, unrelated).

## Phase-3 verification

### The key guarantee: lite loads no heavy modules by default

The most direct, reproducible signal is **which heavy modules are imported
after the app fully initializes**. Measured by importing `app` (full lifespan
init runs) and inspecting `sys.modules`:

| Mode (defaults) | Heavy modules loaded after init |
|---|---|
| **Lite**, no `EMBEDDING_URL` | **none** — no `fastembed`, `onnxruntime`, `chromadb`, `sqlite_vec`, or `feedparser` |
| Full, no `CHROMADB_HOST` | `fastembed`, `onnxruntime`, `chromadb`, `sqlite_vec` (eager RAG + embedded memory init — same posture as Phase 2, which already loaded chromadb + fastembed) |

In **lite** mode the embedded sqlite-vec store is selected only when a hosted
embedding endpoint is configured; with none set, memory stays keyword-only and
the embedding/vector stack is never imported — exactly the Phase-2 lite
behavior. This was asserted at three layers:

- A unit test (`tests/test_vector_backend_selection.py`) asserts
  `select_embedding_provider(lite=True)` returns `None` without an endpoint and
  does not import `fastembed`.
- App-boot inspection (above) confirms `fastembed`/`onnxruntime`/`chromadb`/
  `sqlite_vec`/`feedparser` are absent from `sys.modules` in lite.
- Plugin discovery is lazy: neither the plugin loader nor any plugin module
  (incl. the lightweight tools and `feedparser`) is imported at boot.

### In-process RSS snapshot (indicative)

Measured as `VmRSS` of the Python process right after `import app` completes
(this is **lower** than the Phase-2 numbers above, which boot a real uvicorn
server — so compare modes to each other here, not to the uvicorn table):

| Mode (defaults) | In-process RSS after init |
|---|---|
| Lite, no `EMBEDDING_URL` | ~151 MB |
| Full, no `CHROMADB_HOST` | ~327 MB |

The lite/full gap (~176 MB) is the embedding + vector stack that lite avoids
entirely by default. Lite is comfortably under the §6.2 target (<250 MB idle).

### What changed in each mode

- **Lite defaults** are unchanged from Phase 2 at the resource level: keyword
  memory, API/DuckDuckGo search (never the SearXNG container), no ONNX, no
  plugins loaded, no MCP npx downloads. New features are present but inert until
  configured.
- **Full mode** keeps ChromaDB + SearXNG as before. One behavioral improvement:
  when no ChromaDB server is running, memory now uses the embedded sqlite-vec
  store (which loads fastembed to embed) instead of silently degrading to
  keyword — so full single-user installs get semantic memory with no server.
  This loads the embedding model eagerly, consistent with full mode's existing
  eager-RAG posture.

### Tests

`pytest -m "not slow"`: **3282 passed**, 1 skipped, 5 deselected, **same 3
pre-existing** `tests/test_run_focus.py` failures (path-with-spaces, unrelated
to this work). +77 tests added across Phase 3.

## Conclusion

The Phase-2 low-end baseline is **not regressed**: lite mode loads zero heavy
modules and stays keyword-only/API-search by default, and all new subsystems
(embedded vectors, pluggable embeddings, API search, plugins, UI panels,
lightweight tools) are opt-in or interface-selected and lazy. Full mode retains
ChromaDB/SearXNG and gains embedded-memory as a fallback.
