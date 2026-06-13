# 0003 - Embedded sqlite-vec as the default memory vector backend

## Status

Accepted

## Context

Lodestar's semantic memory recall (and personal-doc RAG) was built on a
standalone **ChromaDB server** reached over HTTP via `chromadb-client`. That
works, but for the low-end / single-user installs Lodestar targets it has real
costs:

- It requires running a separate ChromaDB container (one of the four-container
  Docker stack the planning doc flags as the biggest idle-RAM cost), or a
  manually-run server. A single-user box should not need a dedicated vector-DB
  service.
- The documented `chromadb-client` vs `chromadb` packaging conflict is a
  recurring setup footgun.
- When ChromaDB isn't reachable, memory silently degrades to keyword search —
  so the common single-user "no ChromaDB running" case got *no* semantic
  memory at all.

The memory subsystem is well-shaped for swapping this out: `memory.json` (via
`MemoryManager`) is the **system of record**; the vector store is only ever a
**rebuildable index** over it, exposing a narrow interface
(`add/remove/search/find_similar/rebuild/count/healthy/get_stats`). Both
`NativeMemoryProvider` and `ChatProcessor` consume only that interface.

## Decision

- Add an **embedded vector backend** using
  [`sqlite-vec`](https://github.com/asg017/sqlite-vec) — a tiny prebuilt
  loadable SQLite extension, no server and no ONNX of its own. It implements
  the same interface as the ChromaDB-backed `MemoryVectorStore` and drops in at
  the single `app_initializer` injection point.
- Store vectors in a **dedicated `data/vectors.db`**, separate from the primary
  `app.db`, so the loadable extension and its `vec0` virtual tables never touch
  application schema, migrations, or WAL. The index can be dropped/rebuilt
  without risking user data.
- Make backend selection explicit via a `vector_backend` setting
  (`auto` | `sqlite_vec` | `chromadb`) and `LODESTAR_VECTOR_BACKEND` env
  override, resolved by `src/providers/selection.py`. `auto` picks ChromaDB
  when a `CHROMADB_HOST` is configured (full / multi-user), else the embedded
  store.
- Use cosine distance (`vec0 ... distance_metric=cosine`) so `score = 1 -
  distance` matches the existing ChromaDB store's similarity contract exactly.
  A provider/model **fingerprint** is persisted with the index; a mismatch
  (embedding model changed) drops and rebuilds it rather than querying
  wrong-dimension vectors — the same safeguard the ChromaDB embedding-lanes
  code uses.

## Consequences

- **ChromaDB remains fully supported in full mode** — it is the selected
  backend whenever `CHROMADB_HOST` is set or `vector_backend=chromadb`. This is
  an *addition*, not a replacement.
- **Lite default does not regress the idle-RSS baseline.** The embedded store
  needs an embedding provider; in lite mode without a hosted `EMBEDDING_URL`,
  selection returns no provider and memory stays keyword-only — no ONNX is
  loaded, exactly as before Phase 3. With a hosted endpoint, lite gains real
  semantic memory for free (small sqlite file, no local model).
- **Single-user full installs improve**: previously, "full mode, no ChromaDB
  running" degraded to keyword memory; now it transparently uses the embedded
  store.
- **Safe migration**: because `memory.json` is authoritative,
  `lodestar-memory reindex` (and the existing auto-rebuild-when-empty path in
  `app_initializer`) just recompute the index from the JSON. No memory data is
  moved or at risk.
- Adds one small, non-pure-Python dependency (`sqlite-vec`, wheel-distributed
  loadable extension) to the base requirements — kept out of the lite
  installer's exclude regex so lite installs get it too. RAG over personal
  folders still uses ChromaDB for now; only memory moves to the embedded store
  in this change.
