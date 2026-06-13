# Configuration

Most setup is done inside the app via **Settings**. This page covers the
`.env` file and all environment variables for deployment-level overrides.

---

## Environment variable reference

All `LODESTAR_*` variables have a legacy `ODYSSEUS_*` alias that still works
as a deprecated fallback. A one-line notice is logged at startup when a legacy
name is used. Prefer the `LODESTAR_*` name for new deployments.

### LLM

| Variable | Default | Description |
|---|---|---|
| `LLM_HOST` | `localhost` | Primary LLM server hostname |
| `LLM_HOSTS` | — | Comma-separated list of additional LLM hosts for model discovery |
| `OPENAI_API_KEY` | — | Optional OpenAI API key. Prefer adding providers in the app. |
| `OLLAMA_BASE_URL` | — | Override Ollama endpoint (default: `http://host.docker.internal:11434/v1` in Docker) |
| `LM_STUDIO_URL` | — | LM Studio endpoint |
| `RESEARCH_LLM_ENDPOINT` | — | Override the LLM endpoint used by Deep Research |
| `LLM_CA_BUNDLE` | — | Extra CA bundle PEM for LLM providers with non-standard TLS chains |

### Search & Web

| Variable | Default | Description |
|---|---|---|
| `SEARXNG_INSTANCE` | `http://localhost:8080` | SearXNG instance URL. Docker overrides to `http://searxng:8080`. |
| `SEARXNG_SECRET` | (generated) | SearXNG cookie/CSRF secret. Leave blank for auto-generated. |
| `DATA_BRAVE_API_KEY` | — | Brave Search API key |
| `TAVILY_API_KEY` | — | Tavily API key |
| `SERPER_API_KEY` | — | Serper API key |
| `EXA_API_KEY` | — | Exa API key |

### Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLite database connection string |

### Data directory

| Variable | Default | Description |
|---|---|---|
| `LODESTAR_DATA_DIR` | `./data` | Base data directory for all persistent files |

Legacy: `ODYSSEUS_DATA_DIR`

### Auth & Security

| Variable | Default | Description |
|---|---|---|
| `AUTH_ENABLED` | `true` | Enable/disable login |
| `LOCALHOST_BYPASS` | `false` | Dev-only auth bypass for loopback. Keep false for shared deployments. |
| `SECURE_COOKIES` | `false` | Set true when served through HTTPS at a trusted proxy |
| `LODESTAR_ADMIN_USER` | `admin` | Pre-seed admin username during first setup |
| `LODESTAR_ADMIN_PASSWORD` | (generated) | Pre-seed admin password during first setup |
| `ALLOWED_ORIGINS` | `localhost` | CORS allowed origins |

Legacy: `ODYSSEUS_ADMIN_USER`, `ODYSSEUS_ADMIN_PASSWORD`

### Server

| Variable | Default | Description |
|---|---|---|
| `APP_BIND` | `127.0.0.1` | Bind address. Use `0.0.0.0` for LAN/reverse-proxy access. |
| `APP_PORT` | `7000` | HTTP port |

### Memory / Vector store

| Variable | Default | Description |
|---|---|---|
| `LODESTAR_VECTOR_BACKEND` | `auto` | Vector backend: `auto`, `sqlite_vec`, or `chromadb` |
| `CHROMADB_HOST` | `localhost` | ChromaDB host (Docker overrides to `chromadb`) |
| `CHROMADB_PORT` | `8100` | ChromaDB port (Docker overrides to `8000`) |
| `EMBEDDING_URL` | — | OpenAI-compatible embeddings endpoint |
| `EMBEDDING_API_KEY` | — | Embedding API key |
| `EMBEDDING_MODEL` | — | Embedding model name |
| `FASTEMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local ONNX embedding model |
| `FASTEMBED_CACHE_PATH` | `~/.cache/fastembed` | fastembed model cache location |

### Lite mode

| Variable | Default | Description |
|---|---|---|
| `LODESTAR_LITE` | `false` | Enable lite mode for low-end hardware |

When `true`:
- Memory and personal-doc RAG use keyword search (no ChromaDB)
- Playwright/browser MCP not auto-started
- Smaller SQLite cache/mmap sizes
- Single uvicorn worker

### Upload limits

All upload-limit variables are validated (positive integer) and optional.
Invalid values fail fast at startup.

| Variable | Default | Description |
|---|---|---|
| `LODESTAR_CHAT_UPLOAD_MAX_BYTES` | `10485760` | Chat/agent attachment cap (10 MB) |
| `LODESTAR_GALLERY_UPLOAD_MAX_BYTES` | `104857600` | Gallery image upload cap (100 MB) |
| `LODESTAR_GALLERY_TRANSFORM_UPLOAD_MAX_BYTES` | `26214400` | Gallery transform input cap (25 MB) |
| `LODESTAR_MEMORY_IMPORT_MAX_BYTES` | `10485760` | Memory import file cap (10 MB) |
| `LODESTAR_PERSONAL_UPLOAD_MAX_BYTES` | `26214400` | Personal document upload cap (25 MB) |
| `LODESTAR_EMAIL_COMPOSE_UPLOAD_MAX_BYTES` | `26214400` | Email compose attachment cap (25 MB) |
| `LODESTAR_STT_MAX_AUDIO_BYTES` | `26214400` | Speech-to-text audio cap (25 MB) |
| `LODESTAR_ICS_MAX_BYTES` | `10485760` | Calendar `.ics` import cap (10 MB) |

### Background services

| Variable | Default | Description |
|---|---|---|
| `CLEANUP_INTERVAL_HOURS` | `24` | How often to run cleanup |
| `LODESTAR_INPROCESS_POLLERS` | `1` | Run email pollers in-process. Set to `0` when driving from cron/systemd. |
| `LODESTAR_INPROCESS_TASKS` | `1` | Run scheduled-task runner in-process. Set to `0` for external driver. |
| `LODESTAR_SCRIPT_HOST` | `localhost` | Host for `run_script` scheduled-task action |

Legacy: `ODYSSEUS_INPROCESS_POLLERS`

### Docker Compose service bindings

| Variable | Default | Description |
|---|---|---|
| `CHROMADB_BIND` | `127.0.0.1` | ChromaDB host bind address |
| `NTFY_BIND` | `127.0.0.1` | ntfy host bind address |
| `NTFY_BASE_URL` | `http://localhost:8091` | ntfy public URL |

### GPU (Docker Compose)

| Variable | Default | Description |
|---|---|---|
| `COMPOSE_FILE` | — | GPU overlay: `docker-compose.yml:docker/gpu.nvidia.yml` or `...:docker/gpu.amd.yml` |
| `RENDER_GID` | — | AMD render group GID (find with `getent group render \| cut -d: -f3`) |

---

## Internal API base

`internal_api_base()` returns the loopback URL for agent tool calls. Resolution:

1. `LODESTAR_INTERNAL_BASE` — explicit override
2. `APP_PORT` — `http://127.0.0.1:$APP_PORT`
3. Fallback `http://127.0.0.1:7000`

Legacy: `ODYSSEUS_INTERNAL_BASE`

---

## Settings file

User-visible settings are stored in `data/settings.json` and managed through
**Settings** in the UI. The `.env` file provides deployment-level defaults;
Settings override them at runtime.

---

## Data directory structure

All persistent data lives under `data/` (gitignored):

```
data/
├── app.db                  # Main SQLite database
├── auth.json               # User accounts
├── sessions.json           # Session tokens
├── settings.json           # User settings
├── presets.json            # Chat presets
├── memory.json             # Keyword memory index
├── vectors.db              # Embedded vector memory (sqlite-vec)
├── uploads/                # Chat/agent file uploads
├── personal_docs/          # Personal documents
├── chroma/                 # ChromaDB data (full mode)
├── gallery/                # Gallery images
├── generated_images/       # AI-generated images
├── tts_cache/              # Text-to-speech cache
├── deep_research/          # Research session data
├── mail-attachments/       # Email attachments
├── logs/                   # Application logs
└── ...
```
