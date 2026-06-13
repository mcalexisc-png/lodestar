# Lodestar v0.1.0 — Release Notes

**First release.** June 13, 2026.

Lodestar is a self-hosted AI workspace — your own private chat, agent,
research, email, calendar, and document platform, running on the hardware
you already have. Forked from
[Odysseus](https://github.com/pewdiepie-archdaemon/odysseus) by PewDiePie.

---

## Highlights

### Runs on the hardware you already have

- **Lite mode** for old laptops, mini PCs, and VMs with 2 GB RAM and no GPU.
  One-command installer (`install-lite.sh` / `install-lite.ps1`). Every
  feature works; semantic search degrades to keyword search.
- **Full mode** with ChromaDB vector memory, Playwright browser MCP, and
  multi-worker uvicorn.

### Embedded vector memory

- **SQLite-vec** backend — vector memory runs inside a single SQLite file,
  no ChromaDB server needed. Automatic index rebuild when the embedding
  model changes.

### Plugin system

- **Two-tier architecture:** MCP servers (out-of-process, language-agnostic)
  + in-process Python plugins (small, trusted, zero-startup-cost).
- 7 bundled plugins: file search, CSV reader, datetime, git, SQLite query,
  RSS reader, text statistics.
- Third-party plugins via `pip install` + `lodestar.tools` entry point.

### Everything you'd expect

- **Chat** — streaming, multi-model, presets, attachments
- **Agent** — shell, file I/O, web search, MCP tools, memory, email, calendar
- **Cookbook** — hardware scan, VRAM-aware model recommendations, one-click download/serve
- **Deep Research** — multi-step research with visual reports
- **Compare** — blind side-by-side model comparison
- **Documents** — multi-tab editor with AI assistance
- **Email** — IMAP/SMTP with AI triage
- **Notes & Tasks** — persistent notes, todos, scheduled tasks
- **Calendar** — CalDAV sync
- **Themes** — dark-first theme system with custom theme editor
- **Mobile** — responsive PWA, installable on phones

### Performance

| Metric | Lite | Full |
|---|---|---|
| Cold start | 3.5s | 3.5s |
| Idle RSS | 186 MB | 364 MB |
| Idle CPU | 1.0% | 1.0% |

---

## Install

### Docker (recommended)
```bash
git clone https://github.com/<you>/lodestar.git && cd lodestar
cp .env.example .env
docker compose up -d --build
```

### Native Linux / macOS
```bash
git clone https://github.com/<you>/lodestar.git && cd lodestar
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && python setup.py
python -m uvicorn app:app --host 127.0.0.1 --port 7000
```

### Lite (low-end hardware)
```bash
git clone https://github.com/<you>/lodestar.git && cd lodestar
./install-lite.sh
```

### Windows
```powershell
git clone https://github.com/<you>/lodestar.git && cd lodestar
powershell -ExecutionPolicy Bypass -File .\launch-windows.ps1
```

Open `http://localhost:7000`. The admin password is printed in the terminal on first boot.

---

## Known limitations

- No shell/filesystem sandbox for agent tools
- No per-tool approval gate for admins
- Model endpoint API keys stored in plaintext SQLite
- Cookie name and some DB columns still use legacy `odysseus` names
- Cold start above 3s target

See [CHANGELOG.md](CHANGELOG.md) for the full list.

---

## Credits

Lodestar is a fork of
[Odysseus](https://github.com/pewdiepie-archdaemon/odysseus) by PewDiePie
(Felix Kjellberg). Full credit to the original author and contributors.
See [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md) and [NOTICE](NOTICE).

Deep Research adapted from
[Tongyi DeepResearch](https://github.com/Alibaba-NLP/DeepResearch).
Cookbook built on [llmfit](https://github.com/AlexsJones/llmfit).
Agent built on [opencode](https://github.com/anomalyco/opencode).

---

## License

AGPL-3.0-or-later — see [LICENSE](LICENSE).
