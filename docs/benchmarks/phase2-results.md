# Phase 2 Results — Before / After

Re-run of `docs/benchmarks/phase2-baseline.md`'s measurements after Steps
1-11 of `phase-2/core-lowend`, on the same hardware and method.

## Method

Same as the baseline: AMD Ryzen 7 3750H (8 threads), ~5.9 GB total RAM,
Linux 7.0.11-zen1-1-zen, x86_64, existing `venv/` with the full
`requirements.txt` installed (including `chromadb-client`/`fastembed`).
Cold-start = wall-clock from process launch to the first `GET /api/health`
200, polled every 0.5s. Idle RSS = `VmRSS` from `/proc/<pid>/status`,
sampled ~60s after the process became healthy and idle.

## Results

| Metric | Full (`LODESTAR_LITE=false`) — before | Full — after | Lite (`LODESTAR_LITE=true`) — before | Lite — after |
|---|---|---|---|---|
| Cold start to `/api/health` 200 | ~5.5s | ~3.5s | ~5.5s | ~3.0s |
| Idle RSS (~1 min after boot) | 209,336 KB (~205 MB) | 211,972 KB (~207 MB) | 212,168 KB (~207 MB) | 189,488 KB (~185 MB) |

- **Lite mode idle RSS dropped ~22 MB (~10.6%)** versus baseline, now
  measurably lighter than full mode — the result of Step 4 (lite skips
  eager `get_rag_manager()`/`MemoryVectorStore` ChromaDB+fastembed
  initialization, no Playwright/browser MCP auto-start) actually taking
  effect. Before Phase 2, `LODESTAR_LITE` was a documented no-op and both
  modes were statistically identical.
- **Cold start improved in both modes** (~5.5s → ~3-3.5s). Some of this is
  likely run-to-run variance (single-sample measurements, same as the
  baseline), but lite's larger improvement is consistent with skipping the
  eager RAG/vector-store init on the boot path.
- **Full mode is unchanged in behavior** — same eager initialization path,
  RSS within ~1% of baseline (noise).

## Idle CPU (Step 10)

Not part of the original baseline table, but measured during Step 10: the
60s `_keepalive_loop` in `app.py` was found to call `discover_models()`
(a ~24-port x 2-host scan via a 50-thread pool) on every tick, costing
~600ms aggregate CPU per tick (~1% sustained) even when zero endpoints are
ever discovered (cloud-only/lite setups). A 55s TTL cache inside
`ModelDiscovery.discover_models()` (bypassable via `fresh=True` for the
explicit `/api/discover` rescan) cut this to ~30ms across multiple ticks —
verified over ~4 consecutive 60s windows with only the first triggering a
real scan.

## pytest (fast lane, `-m "not slow"`)

Both modes:

```
3205 passed, 1 skipped, 5 deselected, 3 failed, 71 warnings in ~37-38s
```

Same pass count and the same 3 pre-existing `tests/test_run_focus.py`
failures as the baseline (environment-specific: repo path contains spaces).
**No regressions in either mode.**

## Other Phase 2 changes (not directly RSS/CPU-visible here)

- **Step 5**: native `install-lite.sh` / `install-lite.ps1` installers that
  filter `chromadb-client`/`fastembed`/`onnxruntime` out of the lite venv
  entirely — a real-world lite install will be lighter than this measurement
  (which uses the full dependency set for both modes, to isolate the
  `LODESTAR_LITE` runtime-behavior delta from the dependency-set delta).
- **Step 3**: SQLite WAL + `synchronous=NORMAL` + tuned cache/mmap +
  `busy_timeout` — HDD-friendly write behavior, not expected to show up in
  cold-start/RSS but reduces write-stall risk on spinning disks.
- **Step 6**: first-run hardware wizard (advisory lite/full + provider
  recommendation).
- **Step 7**: added Cerebras to the fast-cloud provider presets (Groq,
  OpenRouter, Together, Mistral, DeepSeek already existed).
- **Step 8**: existing provider/service health-check backend
  (`/api/diagnostics/services`, per-host cooldown + fallback chains in
  `src/llm_core.py`) is now surfaced in Settings > System.
- **Step 9**: confirmed via ADR that "opencode" is only an optional LLM
  provider + design-pattern credit, not a Node/npx runtime dependency; the
  Playwright browser MCP (the actual npx dependency) is independently gated
  behind `LODESTAR_LITE` and degrades gracefully in full mode without
  Node/npx present.
- **Step 11**: CI smoke-test job boots in lite mode, polls `/api/health`,
  and asserts idle RSS stays under 600 MB (informational, generous headroom
  over the ~185 MB measured here).

## Summary

Lite mode now does meaningfully less work at boot than full mode (as
intended), with a measured ~10.6% idle-RSS reduction and faster cold start,
while full mode's behavior and resource use are unchanged within
measurement noise. Test pass rates are identical to baseline in both modes.
