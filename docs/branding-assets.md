# Branding Assets

Asset specifications for Lodestar branding. Supply the files listed below
and place them at the paths indicated.

---

## Tagline

```
steer your own AI — by your own star
```

## ASCII banner

```
              .                 *
       *           .                      .
                 \   .   |   .   /
        .          \      |      /            *
                    \  .  |  .  /
     *  . ─────────  *  L O D E S T A R  *  ───────────  .
                    /  '  |  '  \
        *          /      |      \          .
                 /   '    |    '   \
       .            *           .              *
            steer your own AI — by your own star
```

---

## Required assets

### Logo

| Asset | Sizes | Format | Path | Notes |
|---|---|---|---|---|
| SVG logo | Scalable | SVG | `static/logo.svg` | Primary logo, monochrome preferred |
| PNG logo | 192×192, 512×512 | PNG | `static/icon-192.png`, `static/icon-512.png` | Already exist — replace if updating |
| JPG hero | 1200×630 | JPEG | `docs/lodestar.jpg` | Already exists — replace if updating |

### Favicon

| Asset | Size | Format | Path | Notes |
|---|---|---|---|---|
| Favicon | 32×32 | ICO or SVG | `static/favicon.ico` | Currently missing — supply this |
| Apple touch icon | 180×180 | PNG | `static/apple-touch-icon.png` | For iOS home screen |

### PWA icons

| Asset | Size | Format | Path | Notes |
|---|---|---|---|---|
| PWA icon 192 | 192×192 | PNG | `static/icon-192.png` | Already exists |
| PWA icon 512 | 512×512 | PNG | `static/icon-512.png` | Already exists |
| Maskable icon | 512×512 | PNG | `static/icon-maskable.png` | With safe zone for Android |

### Social card

| Asset | Size | Format | Path | Notes |
|---|---|---|---|---|
| Open Graph image | 1200×630 | JPEG or PNG | `docs/og-image.png` | For link previews on social media |
| Twitter card | 1200×600 | JPEG or PNG | `docs/twitter-card.png` | Optional — can reuse OG image |

---

## Design guidelines

### Colors

Lodestar uses CSS custom properties. The primary palette:

| Token | Hex | Usage |
|---|---|---|
| `--bg` | `#0d1117` | Page background |
| `--card` | `#161b22` | Card/panel background |
| `--fg` | `#c9d1d9` | Primary text |
| `--red` | `#da3633` | Accent, links, active states |
| `--border` | `#30363d` | Borders |

### Typography

- **Primary:** Fira Code (monospace) — for all UI text
- **Fallback:** Inter, system-ui, sans-serif
- **Code blocks:** Fira Code with ligatures

### Icon style

- Monochrome line icons (1.5px stroke)
- Match the existing SVG icons in `static/index.html`
- No filled/solid icons, no multi-color icons

### ASCII art

The ASCII banner above is the primary logotype. Use it in README, terminal
output, and anywhere a text logo is needed. Do not replace with Unicode art.

---

## Files you must supply

| # | File | Status | Action needed |
|---|------|--------|---------------|
| 1 | `static/favicon.ico` | Missing | Create 32×32 ICO from logo |
| 2 | `static/apple-touch-icon.png` | Missing | Create 180×180 PNG from logo |
| 3 | `static/icon-maskable.png` | Missing | Create 512×512 PNG with safe zone |
| 4 | `docs/og-image.png` | Missing | Create 1200×630 social card |
| 5 | `static/logo.svg` | Missing (optional) | Create scalable SVG logo |

The existing `static/icon-192.png` and `static/icon-512.png` are already in
the repo. Replace them only if the logo design changes.
