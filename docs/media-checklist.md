# Media Capture Checklist

Screenshots and demo clips for the README, landing page, and release notes.
All paths are relative to the repo root.

---

## Existing media (do not re-capture unless UI changed)

| File | What | Status |
|---|---|---|
| `docs/chat.gif` | Chat & agent demo | ✅ exists |
| `docs/research.gif` | Deep research report | ✅ exists |
| `docs/compare.gif` | Side-by-side model comparison | ✅ exists |
| `docs/document.gif` | Document editor with AI | ✅ exists |
| `docs/notes.gif` | Notes & tasks | ✅ exists |
| `docs/bg.webm` | Background/tour loop | ✅ exists |
| `docs/chat.webm` | Chat video clip | ✅ exists |
| `docs/compare.webm` | Compare video clip | ✅ exists |
| `docs/document.webm` | Document video clip | ✅ exists |
| `docs/gallery.webm` | Gallery video clip | ✅ exists |
| `docs/notes.webm` | Notes video clip | ✅ exists |
| `docs/research.webm` | Research video clip | ✅ exists |
| `docs/theme.webm` | Theme editor video clip | ✅ exists |
| `docs/lodestar.jpg` | Logo/brand image | ✅ exists |

---

## Screenshots to capture

### Desktop (1920×1080 recommended)

| # | Screen | Path | Alt text | Notes |
|---|--------|------|----------|-------|
| 1 | Chat main view | `docs/screenshot-chat.png` | "Lodestar chat interface with streaming response" | Show sidebar, model picker, streaming response |
| 2 | Agent with tools | `docs/screenshot-agent.png` | "Lodestar agent executing a multi-step task" | Show tool calls in progress |
| 3 | Cookbook hardware scan | `docs/screenshot-cookbook.png` | "Cookbook hardware scan showing model recommendations" | Show VRAM-aware scoring |
| 4 | Deep Research report | `docs/screenshot-research.png` | "Deep Research visual report with citations" | Show the final report view |
| 5 | Settings page | `docs/screenshot-settings.png` | "Lodestar settings with provider configuration" | Show provider setup |
| 6 | Email inbox | `docs/screenshot-email.png` | "Email inbox with AI triage summaries" | Show urgency tags |
| 7 | Calendar | `docs/screenshot-calendar.png` | "Calendar with CalDAV-synced events" | Show event colors |
| 8 | Lite mode banner | `docs/screenshot-lite.png` | "Lodestar running in lite mode on low-end hardware" | Show the lite mode indicator |

### Mobile (375×812 or 390×844, iPhone-style)

| # | Screen | Path | Alt text | Notes |
|---|--------|------|----------|-------|
| 9 | Chat mobile | `docs/screenshot-mobile-chat.png` | "Lodestar chat on mobile" | Responsive layout |
| 10 | Sidebar mobile | `docs/screenshot-mobile-sidebar.png` | "Session sidebar on mobile" | Slide-out behavior |

### Landing page (`docs/index.html`)

| # | Screen | Path | Alt text | Notes |
|---|--------|------|----------|-------|
| 11 | Hero banner | `docs/hero-banner.png` | "Lodestar — steer your own AI" | 1200×630 for social cards |

---

## Video clips to capture

| # | Flow | Path | Duration | Resolution | Notes |
|---|------|------|----------|------------|-------|
| 1 | Chat streaming | `docs/demo-chat.webm` | 15–30s | 1920×1080 | Type a prompt, show streaming response |
| 2 | Agent tool use | `docs/demo-agent.webm` | 20–40s | 1920×1080 | Show agent using shell/file tools |
| 3 | Cookbook download | `docs/demo-cookbook.webm` | 15–30s | 1920×1080 | Hardware scan → model download → serve |
| 4 | Mobile tour | `docs/demo-mobile.webm` | 15–20s | 375×812 | Swipe through features on phone |

---

## Capture guidelines

- **Browser:** Chromium-based, clean profile, no extensions visible
- **Zoom:** 100% browser zoom, default font size
- **Theme:** Dark mode (Lodestar default)
- **Data:** Use demo/sample data, no real emails or API keys visible
- **Terminal:** For install clips, use a clean terminal with 120+ column width
- **GIF vs WebM:** WebM preferred for README (smaller, better quality). GIF for
  fallback in email clients and places that don't support WebM.
- **Naming:** Use lowercase, hyphen-separated names matching the table above

---

## How to capture

### Screenshots (Linux)

```bash
# Full window
grim -g "0,0 1920x1080" docs/screenshot-chat.png

# Or use GNOME Screenshot / Flameshot
gnome-screenshot -w -f docs/screenshot-chat.png
```

### Screenshots (macOS)

```bash
# Full screen
screencapture -x docs/screenshot-chat.png

# Window
screencapture -l <window-id> docs/screenshot-chat.png
```

### Screenshots (Windows)

```bash
# Snipping Tool or Win+Shift+S
```

### Video clips (all platforms)

```bash
# OBS Studio recommended
# Settings: 1920x1080, 30fps, VP8/VP9 codec, CRF 25-30
# Record → Stop → Export as WebM

# Or use built-in screen recording:
# Linux: OBS, Kooha
# macOS: QuickTime (export as HEVC or ProRes, convert with ffmpeg)
# Windows: Xbox Game Bar (Win+G)
```

### Convert GIF → WebM (if needed)

```bash
ffmpeg -i input.gif -c:v libvpx-vp9 -crf 30 -b:v 0 output.webm
```
