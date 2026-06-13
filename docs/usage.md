# Usage Guide

Lodestar is a self-hosted AI workspace. This guide covers the main features.

---

## Chat

The primary interface. Select a model from the dropdown (top-left), type your
message, and press Enter or click Send.

- **Model picker:** Switch between configured providers and models. Filter by
  name, sort by recent/favorites.
- **Presets:** Save and load system prompts + model combinations. The built-in
  "Lodestar" preset is the default.
- **Attachments:** Drag-and-drop or click the paperclip to attach files (images,
  PDFs, text). The attachment size limit is configurable via
  `LODESTAR_CHAT_UPLOAD_MAX_BYTES`.
- **Streaming:** Responses stream in real-time. Markdown, code blocks, and math
  render as they arrive.
- **Sessions:** Create new sessions from the sidebar. Sessions persist across
  restarts. Rename, organize into folders, and search past conversations.

### Slash commands

Type `/` in the chat input to see available commands:

- `/clear` — clear the current session
- `/compact` — summarize and compress the session context
- `/help` — show available commands
- `/web` — enable web search for the next message
- `/doc` — attach a document to the session

### Voice input

Click the microphone icon to record audio. speech-to-text converts your voice
to text before sending. Requires the `faster-whisper` optional dependency for
local STT.

---

## Agent

Agent mode hands the AI tools and lets it execute multi-step tasks autonomously.

### Available tools

| Tool | Description |
|------|-------------|
| **Shell** | Execute bash commands (admin only) |
| **File read/write** | Read and write files on disk (admin only) |
| **Web search** | Search the internet via SearXNG or API providers |
| **Web fetch** | Fetch and read web pages |
| **Memory** | Read and write to persistent memory |
| **Documents** | Access personal documents |
| **MCP tools** | Any registered MCP server tools |
| **Plugin tools** | In-process plugin tools |

### Approval gates

High-risk actions (shell, file write, email send) require explicit admin
approval before execution. The approval prompt shows the exact action and
its risk level.

### Skills

Skills are reusable instruction sets the agent can load. They live in
`data/skills/` and are managed from the Skills panel. Create a skill for
recurring workflows.

---

## Cookbook

Scans your hardware, recommends models that fit, and lets you download and
serve them with one click.

- **Hardware scan:** Detects CPU, RAM, GPU, VRAM. Shows a hardware profile.
- **Model recommendations:** Scores models by fit (architecture age, quant
  format, VRAM/RAM fit, backend support).
- **Download:** Downloads GGUF/FP8/AWQ models from Hugging Face. Progress
  shown in real-time.
- **Serve:** Starts the model with llama.cpp or vLLM. The serve process runs
  in a background `tmux` session.
- **Remote servers:** Connect to remote GPU servers via SSH for download and
  serve.

### Cookbook settings

- **Default backend:** Choose between llama.cpp, vLLM, or Ollama.
- **Port range:** Configure which ports Cookbook uses for serving.
- **Download directory:** Where models are stored (default: `data/huggingface/`).

---

## Deep Research

Multi-step research that gathers, reads, and synthesizes sources into a
visual report.

1. Enter a research question
2. Lodestar generates search queries, fetches pages, reads content, and
   identifies follow-up questions
3. Iterates until satisfied or a limit is reached
4. Produces a structured report with citations

Configure the research model and iteration depth in **Research Settings**.
The research backend runs asynchronously — you can close the panel and
check results later.

---

## Compare

Side-by-side blind model comparison.

1. Select two or more models
2. Enter a prompt
3. Both models respond — displayed side-by-side without labels
4. Vote for your preferred response
5. After voting, reveal which model produced which response

Useful for evaluating model quality without bias.

---

## Documents

A multi-tab document editor with AI assistance.

- **Editor:** Markdown, HTML, CSV with syntax highlighting
- **AI edits:** Select text and ask the AI to rewrite, expand, summarize, or
  correct it
- **File handling:** Open, save, and export documents
- **Personal docs:** Store documents in `data/personal_docs/` for agent access

---

## Memory

Persistent memory the agent can read and write to evolve over time.

- **Categories:** Facts, preferences, instructions, context
- **Search:** Semantic search (ChromaDB with fastembed ONNX) or keyword search
  (lite mode)
- **Import/export:** Bulk import from JSON, export your memory
- **Agent access:** The agent reads relevant memories automatically and can
  add new ones

---

## Email

IMAP/SMTP inbox with AI triage.

### Setup

1. Add an email account in **Settings → Email**
2. Configure IMAP/SMTP server, port, and credentials
3. Enable features: auto-tag, auto-summary, auto-reply drafts, urgency reminders

### Features

- **Inbox:** Browse emails with AI-generated summaries
- **Triage:** Urgency scoring, auto-tagging, spam detection
- **Compose:** AI-assisted email composition
- **CalDAV-aware:** Recognizes calendar invitations

### Limitations

Outlook/Microsoft 365 generally requires OAuth instead of password
authentication. See [docs/email-outlook.md](email-outlook.md) for details.

---

## Notes & Tasks

Quick notes with reminders and a todo list.

- **Notes:** Rich text notes with AI assistance. Pin important notes.
- **Tasks:** Todo list with due dates. The agent can create and complete tasks.
- **Scheduled tasks:** Cron-style tasks the agent can act on. Notification
  channels: ntfy, browser, email.
- **Reminders:** Time-based reminders that trigger notifications.

---

## Calendar

Local-first calendar with CalDAV sync.

- **CalDAV sync:** Connect to Radicale, Nextcloud, Apple, or Fastmail
- **ICS import/export:** Import `.ics` files, export calendars
- **Per-calendar colors:** Color-code different calendars
- **Agent-aware:** The agent can read and create calendar events

### Setup

1. Go to **Settings → Calendar**
2. Add a CalDAV server URL and credentials
3. Select which calendars to sync

---

## Themes

Lodestar ships with a dark-first theme system.

- **Built-in themes:** Select from the theme picker
- **Custom themes:** Create and edit themes in the theme editor
- **CSS variables:** All colors and spacing controlled via CSS custom properties
- **Import/export:** Share themes as JSON files

---

## Mobile

Lodestar is a Progressive Web App (PWA) that works on phones.

- **Responsive:** Adapts to all screen sizes
- **Installable:** Add to home screen from your phone's browser
- **Touch gestures:** Swipe, tap, and long-press throughout

---

## Security basics

- **Auth:** Username/password login with optional 2FA (TOTP)
- **Admin gating:** Shell, file access, email, MCP, and settings are admin-only
- **Session management:** 7-day tokens, revocable per-device
- **Cookies:** Secure flag configurable for HTTPS deployments

See [SECURITY.md](../SECURITY.md) for the full deployment guidance.
