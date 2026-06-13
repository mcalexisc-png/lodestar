# Pre-release QA Results — v0.1.0

## Environment

- **OS:** Linux 7.0.11-zen1 x86_64
- **Python:** 3.14.5 (venv with project dependencies)
- **RAM:** 5.7 GB
- **Cores:** 8
- **Date:** 2026-06-13

## QA matrix

### 1. Native Linux (full mode)

| Check | Result |
|---|---|
| Python syntax (all .py) | ✅ Pass |
| JS syntax (all .js) | ✅ Pass |
| App import + boot | ✅ Pass |
| Plugin discovery (7 plugins) | ✅ Pass |
| sqlite-vec loads | ✅ Pass |
| APP_VERSION = 0.1.0 | ✅ Pass |
| LODESTAR_LITE = false | ✅ Pass |
| Test suite | ✅ 2456/2457 pass (1 pre-existing failure) |

### 2. Native Linux (lite mode)

| Check | Result |
|---|---|
| LODESTAR_LITE=true boot | ✅ Pass |
| Lite mode logging | ✅ Confirmed |
| Keyword memory fallback | ✅ Available |
| Playwright MCP skipped | ✅ Confirmed (not auto-started) |
| Benchmark: cold start | ✅ 3.5s |
| Benchmark: idle RSS | ✅ 186 MB |
| Benchmark: peak RSS | ✅ 187 MB |
| Benchmark: idle CPU | ✅ 1.0% |

### 3. Docker

| Check | Result |
|---|---|
| docker-compose.yml syntax | ✅ Valid YAML |
| Dockerfile exists | ✅ Present |
| entrypoint.sh | ✅ Present |
| Port bindings (127.0.0.1) | ✅ Default loopback |

**Not exercised:** Docker build + runtime (requires Docker daemon).

### 4. Windows (manual checklist)

- [ ] `launch-windows.ps1` creates venv, installs deps, runs setup, starts server
- [ ] `install-lite.ps1` creates lite venv
- [ ] `update_windows.bat` pulls and rebuilds
- [ ] Python 3.11+ detected by `py -3.11`
- [ ] First-run wizard prints admin password
- [ ] Login at http://localhost:7000 works

### 5. macOS (manual checklist)

- [ ] `start-macos.sh` installs Homebrew deps, creates venv, starts on port 7860
- [ ] `build-macos-app.sh` creates .app wrapper
- [ ] Metal GPU detected for Cookbook
- [ ] `LODESTAR_HOST=0.0.0.0` binds to all interfaces

### 6. Plugin system

| Check | Result |
|---|---|
| 7 bundled plugins discovered | ✅ Pass |
| Plugin manifests valid | ✅ Pass |
| Plugin routes (/api/plugins) | ✅ Mounted |
| Capability model (NET/FS/SHELL) | ✅ Defined |

### 7. Embedded vector memory (sqlite-vec)

| Check | Result |
|---|---|
| sqlite-vec extension loads | ✅ Pass |
| vectors.db path correct | ✅ data/vectors.db |
| Vector backend selection | ✅ LODESTAR_VECTOR_BACKEND works |

### 8. Test suite summary

```
2456 passed, 1 failed, 2 skipped, 20 warnings in 76s
```

The single failure (`test_run_focus.py::test_dry_run_prints_command_and_does_not_execute`)
is a pre-existing issue caused by Python 3.14 adding quotes around `sys.executable`
paths. Not a regression from Phase 5 changes.

## Paths not exercised (require manual testing)

| Path | Why |
|---|---|
| Docker full build + runtime | Requires Docker daemon |
| Native macOS | Requires macOS |
| Native Windows | Requires Windows |
| Apple Silicon Metal GPU | Requires M-series Mac |
| Real email integration | Requires IMAP credentials |
| CalDAV sync | Requires CalDAV server |
| MCP server auto-connect | Requires npm/npx |
| Browser MCP (Playwright) | Requires Chromium |
| Cookbook GPU serve | Requires GPU |
