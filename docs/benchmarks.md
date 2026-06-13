# Benchmarks

Performance numbers for Lodestar v0.1.0. All measurements are reproducible
with `scripts/bench_harness.py`.

---

## Method

**Script:** `scripts/bench_harness.py`

**What it measures:**

| Metric | How |
|---|---|
| Cold start | Seconds from `uvicorn` launch to `/api/health` returning 200 |
| Idle RSS | VmRSS from `/proc/<pid>/status` sampled 30 seconds after healthy |
| Peak RSS | Maximum VmRSS during a scripted API load (20 memory writes + 30 GET requests) |
| Idle CPU | Average CPU% over 60 seconds idle using `/proc/<pid>/stat` tick delta |

**What it does NOT measure:**

- No real LLM inference (all API calls hit unauthenticated endpoints)
- No real web search or email (bypassed)
- No real file I/O stress (memory writes only)

This is a **server overhead** benchmark, not an end-to-end latency benchmark.
It measures the fixed cost of running Lodestar, not the variable cost of
model inference.

**Configuration:**

```bash
# Default port 7799, auth disabled, single worker
venv/bin/python scripts/bench_harness.py --mode=lite
venv/bin/python scripts/bench_harness.py --mode=full
venv/bin/python scripts/bench_harness.py --mode=both

# CI / threshold mode (exits non-zero on regression)
venv/bin/python scripts/bench_harness.py --throttle

# Override memory/CPU limits via env
BENCH_MEMORY_LIMIT=1g BENCH_CPU_LIMIT=1.0 venv/bin/python scripts/bench_harness.py
```

**Environment variables used by the harness:**

| Variable | Default | Description |
|---|---|---|
| `BENCH_MEMORY_LIMIT` | `2g` | Memory limit (informational; not enforced without cgroups) |
| `BENCH_CPU_LIMIT` | `2.0` | CPU limit (informational) |

---

## Results — v0.1.0 (Phase 5 release)

**System:** Linux 7.0.11-zen1 x86_64, Python 3.14.5, 5.7 GB RAM, 8 cores

### Lite mode (`LODESTAR_LITE=true`)

| Metric | Value |
|---|---|
| Cold start | 3.5s |
| Idle RSS (30s) | 190,260 KB (186 MB) |
| Peak RSS (load) | 191,100 KB (187 MB) |
| Idle CPU (60s) | 1.0% |

### Full mode (`LODESTAR_LITE=false`)

| Metric | Value |
|---|---|
| Cold start | 3.5s |
| Idle RSS (30s) | 373,136 KB (364 MB) |
| Peak RSS (load) | 373,968 KB (365 MB) |
| Idle CPU (60s) | 1.0% |

### Comparison with Phase 4 baseline

| Metric | Phase 4 lite | Phase 5 lite | Phase 4 full | Phase 5 full |
|---|---|---|---|---|
| Cold start | 3.5s | 3.5s | 4.0s | 3.5s |
| Idle RSS | 185 MB | 186 MB | 363 MB | 364 MB |
| Peak RSS | 186 MB | 187 MB | 378 MB | 365 MB |
| Idle CPU | 1.0% | 1.0% | 1.0% | 1.0% |

### Final pre-release verification (lite mode, 3 runs)

Re-run of `scripts/bench_harness.py --mode=lite` on the release branch,
3 consecutive runs (same machine as above):

| Run | Cold start | Idle RSS (30s) | Peak RSS (load) | Idle CPU (60s) |
|---|---|---|---|---|
| 1 | 3.0s | 187,316 KB (183 MB) | 192,276 KB (188 MB) | 1.0% |
| 2 | 3.0s | 189,096 KB (185 MB) | 191,832 KB (187 MB) | 1.0% |
| 3 | 3.0s | 189,728 KB (185 MB) | 190,888 KB (186 MB) | 1.0% |
| **min** | **3.0s** | 187,316 KB | 190,888 KB | 1.0% |
| **max** | **3.0s** | 189,728 KB | 192,276 KB | 1.0% |
| **avg** | **3.0s** | 188,713 KB (184 MB) | 191,665 KB (187 MB) | 1.0% |

Cold start improved from 3.5s (Phase 5) to 3.0s, an improvement of 0.5s.
The harness reports cold start at 0.5s polling resolution, so the true
value is somewhere in (2.5s, 3.0s]. This is right at the <3s target
boundary — close enough that we consider it met in practice, but it is
not a comfortable margin. The remaining time is dominated by Python
interpreter startup and module imports (FastAPI/uvicorn/SQLite-vec init)
rather than anything specific to Lodestar's own code; further reduction
would require deferring heavier imports (e.g. embedding model loading)
until first use.

### Thresholds (CI regression gate)

| Target | Lite | Full |
|---|---|---|
| Cold start < 6.0s | 3.5s | 3.5s |
| Idle RSS < 250 MB | 186 MB | — |
| Idle RSS < 400 MB | — | 364 MB |
| Peak RSS < 500 MB | 187 MB | — |
| Peak RSS < 600 MB | — | 365 MB |
| Idle CPU < 2.0% | 1.0% | 1.0% |

---

## Low-end hardware numbers

TODO: run on real low-end hardware (old laptop, mini PC, or VM with 2 GB RAM
and 2 cores) and paste results here.

**How to reproduce on low-end hardware:**

```bash
# 1. Clone and install
git clone https://github.com/<you>/lodestar.git
cd lodestar
./install-lite.sh

# 2. Run the benchmark
venv/bin/python scripts/bench_harness.py --mode=both 2>&1 | tee /tmp/bench-results.txt

# 3. Paste the SUMMARY section here, along with:
#    - uname -a output
#    - free -h output
#    - nproc output
```

---

## Benchmark history

Phase-specific results from prior phases are in `docs/benchmarks/`:
- `phase2-baseline.md` / `phase2-results.md`
- `phase3-results.md`
- `phase4-baseline.md` / `phase4-results.md`
