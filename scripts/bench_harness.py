#!/usr/bin/env python3
"""Harness for Phase 4 baseline/regression measurements.

Usage:
    python scripts/bench_harness.py [--mode=lite|full] [--assert]
    python scripts/bench_harness.py --check-deps

Captures:
  - cold_start: seconds from launch to /api/health 200
  - idle_rss_kb: VmRSS ~30s after healthy
  - peak_rss_kb: peak VmRSS during scripted chat
  - idle_cpu_pct: avg CPU% over 60s idle window
"""

import os, sys, time, json, subprocess, tempfile, signal, atexit, re, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# ── config ──
MEMORY_LIMIT = os.environ.get("BENCH_MEMORY_LIMIT", "2g")
CPU_LIMIT = os.environ.get("BENCH_CPU_LIMIT", "2.0")
HEALTH_URL = "http://127.0.0.1:7799/api/health"
BOOT_PORT = "7799"
HARNESS_POLL_INTERVAL = 0.5
HARNESS_MAX_POLLS = 120  # 60s max boot
IDLE_SAMPLE_WAIT = 30
IDLE_CPU_DURATION = 60

def check_deps():
    missing = []
    for cmd in ["curl", "python"]:
        if not subprocess.run(["which", cmd], capture_output=True).returncode == 0:
            missing.append(cmd)
    for mod in ["uvicorn", "fastapi", "httpx"]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        print(f"Missing deps: {', '.join(missing)}")
        sys.exit(1)
    print("All dependencies ok.")
    sys.exit(0)


def _rss_kb(pid):
    try:
        out = subprocess.run(["grep", "VmRSS", f"/proc/{pid}/status"],
                             capture_output=True, text=True, timeout=5)
        m = re.search(r"(\d+)\s+kB", out.stdout)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def _cpu_pct(pid, duration):
    """Return avg CPU% over `duration` seconds using /proc/pid/stat ticks."""
    try:
        import time as _time
        clk_tck = 100  # Linux standard CLK_TCK
        def _pid_cpu_ticks():
            with open(f"/proc/{pid}/stat") as f:
                parts = f.read().split()
            return int(parts[11]) + int(parts[12]) + int(parts[13]) + int(parts[14])
        start = _pid_cpu_ticks()
        _time.sleep(duration)
        end = _pid_cpu_ticks()
        delta_sec = (end - start) / clk_tck
        return round(100.0 * delta_sec / duration, 1)
    except Exception:
        return None


def wait_for_health(url, max_polls, interval):
    for i in range(max_polls):
        try:
            r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip() == "200":
                return (i + 1) * interval
        except Exception:
            pass
        time.sleep(interval)
    return None


def scripted_load(pid, base_url):
    """Drive API load to measure peak RSS. No auth, no LLM needed."""
    import httpx, time as _time
    peak = _rss_kb(pid) or 0

    endpoints = [
        ("GET", f"{base_url}/api/health"),
        ("GET", f"{base_url}/api/version"),
        ("GET", f"{base_url}/api/runtime"),
    ]

    # Memory write stress: add 20 memories via POST
    memory_url = f"{base_url}/api/memory"
    for i in range(20):
        try:
            with httpx.Client(timeout=10) as c:
                c.post(memory_url, json={
                    "text": f"Benchmark memory entry {i}: testing memory subsystem allocation patterns.",
                    "category": "fact",
                    "source": "benchmark",
                })
        except Exception:
            pass
        rss = _rss_kb(pid)
        if rss and rss > peak:
            peak = rss
        _time.sleep(0.1)

    # Basic GET loads
    for method, url in endpoints * 10:
        try:
            with httpx.Client(timeout=10) as c:
                c.get(url)
        except Exception:
            pass
        rss = _rss_kb(pid)
        if rss and rss > peak:
            peak = rss

    # Memory read: list all memories
    try:
        with httpx.Client(timeout=10) as c:
            c.get(memory_url)
    except Exception:
        pass
    rss = _rss_kb(pid)
    if rss and rss > peak:
        peak = rss

    return peak


def run_harness(mode, do_assert=False):
    os.makedirs("data", exist_ok=True)
    env = os.environ.copy()
    env["LODESTAR_LITE"] = "true" if mode == "lite" else "false"
    env["APP_PORT"] = BOOT_PORT
    if "AUTH_ENABLED" not in env:
        env["AUTH_ENABLED"] = "false"

    print(f"\n{'='*60}")
    print(f"Phase 4 Benchmark — mode={mode}")
    print(f"{'='*60}")

    # ── Boot ──
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app",
         "--host", "127.0.0.1", "--port", BOOT_PORT, "--workers", "1"],
        env=env, cwd=REPO,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    pid = proc.pid

    def cleanup():
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    atexit.register(cleanup)

    # ── Cold start ──
    print(f"  Booting (LODESTAR_LITE={mode})...", end=" ", flush=True)
    cold_time = wait_for_health(HEALTH_URL, HARNESS_MAX_POLLS, HARNESS_POLL_INTERVAL)
    if cold_time is None:
        print("FAILED to become healthy")
        proc.kill()
        return None
    print(f"healthy at {cold_time:.1f}s")

    # ── Idle RSS ~30s after healthy ──
    time.sleep(IDLE_SAMPLE_WAIT - cold_time if cold_time < IDLE_SAMPLE_WAIT else 2)
    idle_rss = _rss_kb(pid)
    print(f"  Idle RSS ({IDLE_SAMPLE_WAIT}s post-healthy): {idle_rss} KB")

    # ── Idle CPU over 60s ──
    print(f"  Measuring idle CPU over {IDLE_CPU_DURATION}s...", end=" ", flush=True)
    idle_cpu = _cpu_pct(pid, IDLE_CPU_DURATION)
    print(f"{idle_cpu:.1f}%" if idle_cpu is not None else "N/A")

    # ── Peak RSS during load ──
    print(f"  Running scripted API load...", end=" ", flush=True)
    peak_rss = scripted_load(pid, f"http://127.0.0.1:{BOOT_PORT}")
    print(f"peak RSS: {peak_rss} KB")

    # ── Cleanup ──
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

    results = {
        "mode": mode,
        "cold_start_seconds": round(cold_time, 2),
        "idle_rss_kb": idle_rss,
        "peak_rss_during_chat_kb": peak_rss,
        "idle_cpu_pct": round(idle_cpu, 1) if idle_cpu is not None else None,
    }
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["lite", "full", "both"], default="both")
    parser.add_argument("--throttle", action="store_true", help="Assert thresholds (CI mode)")
    parser.add_argument("--check-deps", action="store_true")
    args = parser.parse_args()

    if args.check_deps:
        check_deps()

    modes = ["lite", "full"] if args.mode == "both" else [args.mode]
    all_results = {}
    for mode in modes:
        r = run_harness(mode, do_assert=args.throttle)
        if r:
            all_results[mode] = r

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for mode, r in all_results.items():
        print(f"\n  [{mode.upper()}]")
        print(f"    Cold start:         {r['cold_start_seconds']}s")
        print(f"    Idle RSS (30s):     {r['idle_rss_kb']} KB")
    print(f"    Peak RSS (load):    {r['peak_rss_during_chat_kb']} KB")
    print(f"    Idle CPU (60s):     {r['idle_cpu_pct']}%")

    # Assert thresholds if CI mode
    if args.throttle:
        thresholds = {
            "lite": {"cold_start_max": 6.0, "idle_rss_max": 250_000, "peak_rss_max": 500_000, "idle_cpu_max": 2.0},
            "full": {"cold_start_max": 8.0, "idle_rss_max": 350_000, "peak_rss_max": 600_000, "idle_cpu_max": 3.0},
        }
        failures = []
        for mode, r in all_results.items():
            t = thresholds.get(mode, thresholds["lite"])
            if r["cold_start_seconds"] > t["cold_start_max"]:
                failures.append(f"[{mode}] cold_start {r['cold_start_seconds']}s > {t['cold_start_max']}s")
            if r["idle_rss_kb"] and r["idle_rss_kb"] > t["idle_rss_max"]:
                failures.append(f"[{mode}] idle_rss {r['idle_rss_kb']} KB > {t['idle_rss_max']} KB")
            if r["peak_rss_during_chat_kb"] and r["peak_rss_during_chat_kb"] > t["peak_rss_max"]:
                failures.append(f"[{mode}] peak_rss {r['peak_rss_during_chat_kb']} KB > {t['peak_rss_max']} KB")
            if r["idle_cpu_pct"] and r["idle_cpu_pct"] > t["idle_cpu_max"]:
                failures.append(f"[{mode}] idle_cpu {r['idle_cpu_pct']}% > {t['idle_cpu_max']}%")
        if failures:
            print("\n  ❌ THRESHOLD FAILURES:")
            for f in failures:
                print(f"    {f}")
            sys.exit(1)
        else:
            print("\n  ✅ All thresholds passed.")

    return all_results


if __name__ == "__main__":
    main()
