# Phase 4 Baseline Measurements

Captured at start of `phase-4/optimization`, before any optimization changes.
All numbers from a single local run on the hardware/method below.
Comparison baseline for every subsequent optimization.

## Method

- **Hardware**: AMD Ryzen 7 3750H (8 threads), ~5.9 GB total RAM
  (`/proc/meminfo` MemTotal), Linux, x86_64.
- **Python**: 3.14.5 (venv), `pip install -r requirements.txt` (full default
  dependency set, including `chromadb-client`, `fastembed`, `sqlite-vec`).
- **Boot command**: `python -m uvicorn app:app --host 127.0.0.1 --port 7799
  --workers 1`, no `.env` file, defaults only.
- **Memory cap**: local (no Docker/systemd-run memory limit — 5.9 GB host has
  >2 GB headroom for the process).
- **Cold-start time**: wall-clock from process launch to first successful
  `GET /api/health` returning 200, polled every 0.5s.
- **Idle RSS**: `VmRSS` from `/proc/<pid>/status`, sampled ~30s after healthy.
- **Idle CPU**: `/proc/<pid>/stat` CPU ticks sampled across 60s idle window.
- **Peak RSS (load)**: peak `VmRSS` during scripted load: 20x `POST /api/memory`
  + 30x `GET /api/{health,version,runtime}`.

## Results

| Metric | Lite (`LODESTAR_LITE=true`) | Full (`LODESTAR_LITE=false`) |
|---|---|---|
| Cold start to `/api/health` 200 | 4.0s | 4.5s |
| Idle RSS (30s post-healthy) | 186,712 KB (~182 MB) | 360,120 KB (~352 MB) |
| Peak RSS (scripted load) | 190,768 KB (~186 MB) | 362,424 KB (~354 MB) |
| Idle CPU (60s window) | 1.1% | 1.1% |

## Comparison to Phase 2/3

| Metric | Phase 2 Lite | Phase 3 Lite | Phase 4 Lite (now) | Phase 2 Full | Phase 3 Full | Phase 4 Full (now) |
|---|---|---|---|---|---|---|
| Cold start | ~3.0s | ~3.0s | **4.0s** | ~3.5s | ~3.5s | **4.5s** |
| Idle RSS | ~185 MB | ~185 MB | **~182 MB** | ~207 MB | ~207 MB | **~352 MB** |

Key observations:
- **Full mode RSS regressed significantly** from ~207 MB (Phase 2/3) to ~352 MB.
  Likely caused by Phase 3 additions (sqlite-vec embedded vector store,
  `select_vector_store` in `app_initializer`, embedding provider selection)
  loading additional modules at boot.
- **Cold start slowed** in both modes by ~1s vs Phase 2/3. This may be
  attributable to the same Phase 3 additions.
- **Lite mode idle RSS stable** at ~182 MB — no regression.
- **Idle CPU** already low at ~1.1% (keepalive loop), but not yet at 0%.

## Targets (from §6.2)

| Target | Lite (current) | Full (current) | Met? |
|---|---|---|---|
| Cold start < 3s (SSD) | 4.0s ❌ | 4.5s ❌ | Both need ~1-1.5s improvement |
| Idle RSS < 250 MB | 182 MB ✅ | 352 MB ❌ | Full mode needs ~102 MB reduction |
| Peak RSS < 600 MB | 186 MB ✅ | 354 MB ✅ | Both well under |
| Idle CPU ≈ 0% | 1.1% ❌ | 1.1% ❌ | Needs further ~1% reduction |

## Harness

`scripts/bench_harness.py` — reusable for before/after comparisons.
Usage: `python scripts/bench_harness.py --mode=lite|full|both`
