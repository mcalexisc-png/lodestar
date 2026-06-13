#!/bin/bash
# Lodestar — native lite installer for low-end Linux/macOS hardware.
#
#   ./install-lite.sh
#
# Sets up a local Python environment with the heavy vector-search stack
# (chromadb-client, fastembed, onnxruntime) left out, runs first-run setup,
# and launches the app with LODESTAR_LITE=true. Safe to re-run; it skips work
# that's already done.
#
# Lite mode (see src/constants.py LODESTAR_LITE):
#   - no ChromaDB-backed RAG / vector memory (keyword search instead)
#   - no Playwright/browser MCP auto-start
#   - smaller SQLite cache_size/mmap_size
#   - single uvicorn worker
#
# For a GPU workstation or to use Personal Docs RAG / semantic memory, use
# ./start-macos.sh, launch-windows.ps1, or `pip install -r requirements.txt`
# instead.
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# Load .env so APP_PORT and APP_BIND are available without re-typing them on
# the command line every run — consistent with how app.py reads them via
# python-dotenv. Variables already set in the shell take priority over .env.
if [ -f .env ]; then
    while IFS='=' read -r key value; do
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${key// }" ]] && continue
        value="${value%%#*}"
        value="${value#"${value%%[![:space:]]*}"}"
        value="${value%"${value##*[![:space:]]}"}"
        [ -n "$key" ] && [ -z "${!key+x}" ] && export "$key=$value"
    done < .env
fi

# Shell overrides (LODESTAR_PORT / LODESTAR_HOST) take top priority, then .env
# values (APP_PORT / APP_BIND), then built-in defaults.
PORT="${LODESTAR_PORT:-${ODYSSEUS_PORT:-${APP_PORT:-7000}}}"
HOST="${LODESTAR_HOST:-${ODYSSEUS_HOST:-${APP_BIND:-127.0.0.1}}}" # Set APP_BIND=0.0.0.0 in .env for LAN/Tailscale access.
PROBE_HOST="$HOST"
if [ "$PROBE_HOST" = "0.0.0.0" ] || [ "$PROBE_HOST" = "::" ]; then
    PROBE_HOST="127.0.0.1"
fi

# Friendly message on any failure — re-running is safe (every step is idempotent).
trap 'echo; echo "✗ Setup failed above. It is safe to re-run ./install-lite.sh."; exit 1' ERR

echo "▶ Lodestar lite install (low-end hardware)"

# Fail fast if the port is already taken (e.g. a previous run still running).
if (exec 3<>"/dev/tcp/$PROBE_HOST/$PORT") 2>/dev/null; then
    echo "✗ Port $PORT is already in use on $PROBE_HOST. Stop what's using it, or pick another port:"
    echo "    LODESTAR_PORT=7900 ./install-lite.sh"
    exit 1
fi

# 1. Find a Python 3.11+ to build the environment with.
PY=""
for cand in python3 python3.13 python3.12 python3.11; do
    p="$(command -v "$cand" 2>/dev/null)" || continue
    if "$p" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)' 2>/dev/null; then
        PY="$p"; break
    fi
done

if [ -z "$PY" ] || [ ! -x "$PY" ]; then
    echo "✗ Couldn't find a Python 3.11+ to build the environment with."
    echo "  Install Python 3.11 or newer, then re-run this script."
    exit 1
fi
echo "  (using $("$PY" --version 2>&1) at $PY)"

# 2. Python environment + lite dependencies (kept inside the repo, in venv/).
if [ ! -d venv ]; then
    echo "▶ Creating Python environment…"
    "$PY" -m venv venv
fi
VENV_PY="./venv/bin/python3"

# Lite installs skip the heavy ChromaDB/ONNX vector-search stack. The app
# already degrades gracefully without these (LODESTAR_LITE=true skips the
# code paths that would use them — see src/constants.py LODESTAR_LITE).
LITE_EXCLUDE_REGEX='^(chromadb-client|fastembed|onnxruntime)([><=! ].*)?$'
LITE_REQ_FILE="venv/.requirements-lite.txt"
grep -viE "$LITE_EXCLUDE_REGEX" requirements.txt > "$LITE_REQ_FILE"

REQ_HASH="$(md5sum "$LITE_REQ_FILE" | cut -d' ' -f1)"
REQ_HASH_FILE="venv/.requirements_hash_lite"
if [ ! -f "$REQ_HASH_FILE" ] || [ "$REQ_HASH" != "$(cat "$REQ_HASH_FILE" 2>/dev/null)" ]; then
  echo "▶ Installing Python packages (first run downloads a few — can take a few minutes)…"
  "$VENV_PY" -m pip install --quiet --upgrade pip
  # Not --quiet: this is the slow step, so show progress (and any real errors).
  "$VENV_PY" -m pip install -r "$LITE_REQ_FILE"
  echo "$REQ_HASH" > "$REQ_HASH_FILE"
else
  echo "▶ Python packages up to date — skipping install"
fi

# 3. First-run setup: creates data dirs and prints an initial admin password
#    the first time (idempotent — does nothing if already set up). Suppress
#    its manual run hint — we launch the server ourselves just below.
echo "▶ Preparing Lodestar…"
LODESTAR_SKIP_RUN_HINT=1 "$VENV_PY" setup.py

# 4. Launch in lite mode. Bind to loopback by default; opt into LAN/Tailscale
#    with LODESTAR_HOST=0.0.0.0. Single worker is the uvicorn default but is
#    made explicit here since lite mode targets memory-constrained machines.
URL_HOST="$HOST"
if [ "$URL_HOST" = "0.0.0.0" ] || [ "$URL_HOST" = "::" ]; then
    URL_HOST="127.0.0.1"
fi
URL="http://$URL_HOST:$PORT"

trap - ERR

echo
echo "▶ Starting Lodestar (lite mode) at $URL"
echo "  (this takes a few seconds; press Ctrl+C here to stop)"
echo
LODESTAR_LITE=true exec "$VENV_PY" -m uvicorn app:app --host "$HOST" --port "$PORT" --workers 1
