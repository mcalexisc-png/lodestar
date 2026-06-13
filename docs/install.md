# Installation

Lodestar supports several install paths. Pick the one that matches your
hardware and comfort level.

## Requirements

- Python 3.11+ (3.12 recommended)
- 4 GB RAM minimum (2 GB for lite mode)
- tmux (for Cookbook background downloads/serves; optional otherwise)
- Git

---

## Docker (recommended)

```bash
git clone https://github.com/<you>/lodestar.git
cd lodestar
cp .env.example .env       # optional but recommended
docker compose up -d --build
```

Open `http://localhost:7000` when containers are healthy.

To include optional extras (PDF viewer, Office extraction; AGPL PyMuPDF):

```bash
docker compose build --build-arg INSTALL_OPTIONAL=true
docker compose up -d
```

### First-run wizard

On first boot Lodestar creates an admin account (`admin` unless
`LODESTAR_ADMIN_USER` is set) and prints a temporary password in the terminal.
For Docker, find it in:

```bash
docker compose logs lodestar | grep -i "temporary password"
```

Use that password for the first login, then change it in **Settings**.

### GPU support

See the GPU overlay section in the main README for NVIDIA and AMD setup.

---

## Native Linux / macOS

```bash
git clone https://github.com/<you>/lodestar.git
cd lodestar
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python setup.py
python -m uvicorn app:app --host 127.0.0.1 --port 7000
```

Requirements: Python 3.11+. The core app (chat, agent, memory, documents,
email, calendar, deep research) runs fully native. Cookbook background
downloads and serves use `tmux`.

Use `--host 0.0.0.0` only when you intentionally want LAN/reverse-proxy access.

---

## Native-lite (low-end hardware)

For old laptops, mini PCs, or any machine with limited RAM/CPU and no GPU.
Skips the ChromaDB/ONNX vector-search stack and launches with `LODESTAR_LITE=true`.

**Linux / macOS:**

```bash
git clone https://github.com/<you>/lodestar.git
cd lodestar
./install-lite.sh
```

**Windows:**

```powershell
git clone https://github.com/<you>/lodestar.git
cd lodestar
powershell -ExecutionPolicy Bypass -File .\install-lite.ps1
```

Both scripts create a venv, install the lite dependency set, run first-run
setup (prints the admin password), and start the server on
`http://127.0.0.1:7000`. Safe to re-run.

To switch a full install to lite mode (or back) without reinstalling:

```bash
# In .env
LODESTAR_LITE=true    # or false
```

Then restart the server.

### What lite mode changes

- Memory and personal-doc RAG fall back to keyword search (no ChromaDB)
- Playwright/browser MCP server is not auto-started
- Smaller SQLite cache/mmap sizes
- Single uvicorn worker
- Web search uses API provider instead of SearXNG container

Every feature still works; semantic search just degrades to keyword search.

---

## Apple Silicon (macOS)

Docker on macOS cannot use the Metal GPU. For GPU-accelerated Cookbook on an
M-series Mac, run Lodestar natively:

```bash
git clone https://github.com/<you>/lodestar.git
cd lodestar
./start-macos.sh
```

Opens at `http://127.0.0.1:7860`. The script installs Homebrew deps, creates
the venv, runs setup, and starts uvicorn on port 7860 (because AirPlay often
holds 7000).

To expose to your phone over a trusted LAN/VPN (Tailscale):

```bash
LODESTAR_HOST=0.0.0.0 ./start-macos.sh
# then open http://<tailscale-ip>:7860
```

To build a clickable app wrapper:

```bash
./build-macos-app.sh
```

### macOS troubleshooting

- vLLM/SGLang are CUDA/ROCm-only and do not run on macOS
- MLX-only models are not served by Lodestar
- llama.cpp and Ollama are used for Metal inference
- If `python` points at an older interpreter, use `/opt/homebrew/bin/python3.11`

---

## Native Windows

**One-command launcher** (creates venv, installs deps, runs setup, starts
server; safe to re-run):

```powershell
git clone https://github.com/<you>/lodestar.git
cd lodestar
powershell -ExecutionPolicy Bypass -File .\launch-windows.ps1
```

Or manually:

```powershell
git clone https://github.com/<you>/lodestar.git
cd lodestar
py -3.11 -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python setup.py
python -m uvicorn app:app --host 127.0.0.1 --port 7000
```

If `python` points at an older interpreter, use `py -3.12` (or another
installed 3.11+ version).

**Requirements:** Python 3.11+. The core app runs fully native. For full
**Cookbook** background model downloads and the agent shell tool, also install
[Git for Windows](https://git-scm.com/download/win) (provides `bash.exe`).

Local GPU *serving* of vLLM/SGLang needs Linux/WSL2; for a local model on
Windows, [Ollama](https://ollama.com/download) is the easiest path — point
Lodestar at `http://localhost:11434/v1` in Settings.

---

## Provider setup

After installation, configure your LLM provider in **Settings**:

1. **Local models (Ollama, llama.cpp, vLLM):** Start your model server, then
   add its URL in Settings (e.g., `http://localhost:11434/v1` for Ollama).
2. **API providers (OpenAI, Anthropic, OpenRouter, etc.):** Add your API key
   in Settings. Lodestar discovers available models automatically.
3. **Web search:** SearXNG runs automatically in Docker. For native installs,
   either run SearXNG separately or configure an API search provider (Brave,
   Tavily, DuckDuckGo) in Settings.

---

## Updating

### Docker

```bash
cd lodestar
git pull
docker compose up -d --build
```

### Native

```bash
cd lodestar
git pull
source venv/bin/activate
pip install -r requirements.txt
# Restart the server
```

### Windows

```powershell
cd lodestar
git pull
venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Restart the server
```

Or use the update helper:

```powershell
.\update_windows.bat
```

---

## Troubleshooting

### `chromadb-client` conflicts with embedded ChromaDB

If `chromadb-client` is installed alongside the full `chromadb` package,
Lodestar starts but ChromaDB silently falls back to HTTP-only mode and fails.

```bash
./venv/bin/pip uninstall chromadb-client -y
./venv/bin/pip install --force-reinstall chromadb
```

### HTTPS + LAN/Tailscale exposure

1. Change bind address: `APP_BIND=0.0.0.0` in `.env`
2. Generate a locally-trusted cert with [mkcert](https://github.com/FiloSottile/mkcert):
   ```bash
   mkcert -install
   mkcert -cert-file cert.pem -key-file key.pem 192.168.1.100 tailscale-ip
   ```
3. Run with certs:
   ```bash
   python -m uvicorn app:app --host 0.0.0.0 --port 7000 --ssl-certfile=cert.pem --ssl-keyfile=key.pem
   ```

### Ollama with Docker

Add this endpoint in Settings:

```text
http://host.docker.internal:11434/v1
```

Ollama must listen outside its own loopback:

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

### Useful diagnostics

```bash
docker compose ps
docker compose logs --tail=120 lodestar
docker compose logs lodestar | grep -E 'ChromaDB|MemoryVectorStore|DEGRADED'
```
