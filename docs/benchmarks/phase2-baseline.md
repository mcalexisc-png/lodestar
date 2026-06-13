# Phase 2 Baseline Measurements

Captured at the start of `phase-2/core-lowend`, before any optimization
changes. All numbers are from a single local run on the hardware/method below
and are meant as a relative before/after comparison, not an absolute
benchmark.

## Method

- **Hardware**: AMD Ryzen 7 3750H (8 threads), ~5.9 GB total RAM
  (`/proc/meminfo` MemTotal), Linux 7.0.11-zen1-1-zen, x86_64.
- **Python**: 3.14.5 (system), fresh `venv/` created in the repo root,
  `pip install -r requirements.txt` (full default dependency set, including
  `chromadb-client` and `fastembed`).
- **Boot command**: `python -m uvicorn app:app --host 127.0.0.1 --port <port>`,
  no `.env` file present (defaults only), existing `data/app.db` from prior
  use (not modified).
- **Cold-start time**: wall-clock from process launch to the first successful
  `GET /api/health` returning 200, polled every 0.5s.
- **Idle RSS**: `VmRSS` from `/proc/<pid>/status`, sampled ~30s-2min after the
  process became healthy and idle (no requests in flight).
- **Tests**: `python -m pytest -q -m "not slow"` (fast lane).

## Results

| Metric | `LODESTAR_LITE=false` (full) | `LODESTAR_LITE=true` |
|---|---|---|
| Cold start to `/api/health` 200 | ~5.5s (ready by 11th 0.5s poll) | ~5.5s (ready by 11th 0.5s poll) |
| Idle RSS (~1-3 min after boot) | 209,336 KB (~205 MB) | 212,168 KB (~207 MB) |

Lite and full mode are statistically identical, as expected — `LODESTAR_LITE`
is currently a documented no-op (`src/constants.py:84-87`). Both runs install
and import `chromadb-client`/`fastembed` etc. at boot via the eager
`get_rag_manager()` call in `app.py` (~line 475) and the memory-vector
initialization path in `src/app_initializer.py`.

## pytest (fast lane, `-m "not slow"`)

```
3205 passed, 1 skipped, 5 deselected, 3 failed, 71 warnings in 63.13s
```

**The 3 failures are pre-existing and environment-specific, not caused by
this branch.** All three are in `tests/test_run_focus.py` and fail because
the repo is checked out at a path containing spaces
(`/home/garuda/Desktop/Own forked Projects/lodestar`), so `sys.executable`
(the venv's `python` path) gets quoted when building a shell command string,
but the test's expected string assumes no quoting is needed. Example diff:

```
- .../venv/bin/python -m pytest -m 'area_services and sub_cookbook'
+ '.../venv/bin/python' -m pytest -m 'area_services and sub_cookbook'
```

These will be re-checked at Step 12 but are not part of the
before/after delta this phase is measuring.

## What Phase 2 should change in these numbers

- **Cold start / idle RSS**: expected to drop once Step 2 (lazy imports) and
  Step 4 (lite mode skips eager `get_rag_manager()` / `MemoryVectorStore`
  ChromaDB+fastembed init) land — lite mode in particular should no longer
  pay the ONNX/chromadb-client import + connection cost at all.
- **pytest pass count**: should stay at 3205 passed (not reduced) for both
  modes; the 3 environment-specific failures are out of scope.
