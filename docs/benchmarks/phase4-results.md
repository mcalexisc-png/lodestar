# Phase 4 Results — post Steps 1–5

All numbers from `scripts/bench_harness.py` on same hardware as baseline.

## Lite Mode

| Metric | Baseline | After Steps 1–5 | Δ |
|---|---|---|---|
| Cold start | 4.0s | **3.5s** | **−0.5s** ✅ |
| Idle RSS | 186,712 KB | 185,228 KB | −1,484 KB |
| Peak RSS (load) | 190,768 KB | 190,860 KB | +92 KB |
| Idle CPU (60s) | 1.1% | 1.0% | −0.1% |

## Full Mode

| Metric | Baseline | After Steps 1–5 | Δ |
|---|---|---|---|
| Cold start | 4.5s | **4.0s** | **−0.5s** ✅ |
| Idle RSS | 360,120 KB | 371,388 KB | +11,268 KB |
| Peak RSS (load) | 362,424 KB | 387,372 KB | +24,948 KB |
| Idle CPU (60s) | 1.1% | 1.0% | −0.1% |

## Event-loop health (pyinstrument)

pyinstrument ASGI-middlware profiles on cold-start lite app:

| Endpoint | Duration | Notes |
|---|---|---|
| `GET /api/health` | 0.008s | Trivial |
| `GET /api/models` | 0.021s | 0.005s `run_sync_in_worker_thread` (healthy) |
| `GET /api/runtime` | 0.029s | Async path clear |
| `POST /api/presets/expand` | 0.024s | `_resolve_model` 0.012s (incl. one-time SSL ctx load 0.006s); `Query.all` 0.004s |

No synchronous blocking detected in request path. All async callers of `_resolve_model` return promptly. The `httpx.AsyncClient` is created lazily on first use (one-time SSL context load ~6ms).

## Thresholds vs §6.2 targets

| Target | Lite | Full |
|---|---|---|
| Cold start < 3s | 3.5s ❌ | 4.0s ❌ |
| Idle RSS < 250 MB | 181 MB ✅ | 363 MB ❌ |
| Peak RSS < 600 MB | 186 MB ✅ | 378 MB ✅ |
| Idle CPU ≈ 0% | 1.0% ❌ | 1.0% ❌ |

Still short of the <3s cold-start target. Further gains would require on-first-use module loading (not just background-init deferred).
