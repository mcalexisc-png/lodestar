// pluginPanels.js — render safe, plugin-registered UI panels.
//
// Plugins (Tier 2, in-process) may register a UI panel as one of two SAFE
// shapes returned by GET /api/plugins/panels:
//
//   { type: "schema", title, widgets: [...] }   declarative widgets from a
//       fixed vocabulary (heading/text/list/key_value/link/badge), rendered
//       here with DOM APIs only — textContent, never innerHTML — so plugin
//       data can never inject markup or scripts into the host page.
//
//   { type: "iframe", title, url, height }       a sandboxed <iframe>. The
//       sandbox attribute withholds allow-same-origin, so the framed page
//       cannot touch the host page's DOM, cookies, or storage.
//
// There is deliberately NO path for a plugin to inject arbitrary JS into the
// vanilla frontend.

const API = window.location.origin;

const ALLOWED_WIDGETS = new Set([
  'heading', 'text', 'list', 'key_value', 'link', 'badge',
]);

export async function loadPluginPanels() {
  try {
    const res = await fetch(`${API}/api/plugins/panels`);
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.panels) ? data.panels : [];
  } catch (e) {
    console.warn('plugin panels load failed', e);
    return [];
  }
}

// Build a panel element from a sanitized spec. Returns an HTMLElement.
export function renderPanel(panel) {
  const root = document.createElement('section');
  root.className = 'plugin-panel';
  root.dataset.plugin = String(panel.plugin || '');

  const header = document.createElement('h3');
  header.className = 'plugin-panel-title';
  header.textContent = String(panel.title || panel.plugin || 'Plugin');
  root.appendChild(header);

  if (panel.type === 'iframe') {
    const frame = document.createElement('iframe');
    // Sandbox WITHOUT allow-same-origin: the framed document gets a unique
    // opaque origin and cannot reach the host page. allow-scripts lets the
    // plugin's own page run, but isolated from us.
    frame.setAttribute('sandbox', 'allow-scripts allow-forms');
    frame.setAttribute('referrerpolicy', 'no-referrer');
    frame.setAttribute('loading', 'lazy');
    frame.src = String(panel.url || '');
    frame.style.width = '100%';
    frame.style.border = '0';
    const h = Number(panel.height) || 360;
    frame.style.height = `${Math.max(120, Math.min(h, 1200))}px`;
    root.appendChild(frame);
    return root;
  }

  // Default: declarative schema panel.
  const widgets = Array.isArray(panel.widgets) ? panel.widgets : [];
  for (const w of widgets) {
    if (!w || !ALLOWED_WIDGETS.has(w.type)) continue;
    root.appendChild(renderWidget(w));
  }
  return root;
}

function renderWidget(w) {
  switch (w.type) {
    case 'heading': {
      const el = document.createElement('h4');
      el.textContent = String(w.text || '');
      return el;
    }
    case 'text': {
      const el = document.createElement('p');
      el.textContent = String(w.text || '');
      return el;
    }
    case 'list': {
      const ul = document.createElement('ul');
      for (const item of (w.items || [])) {
        const li = document.createElement('li');
        li.textContent = String(item);
        ul.appendChild(li);
      }
      return ul;
    }
    case 'key_value': {
      const dl = document.createElement('dl');
      dl.className = 'plugin-panel-kv';
      const pairs = w.pairs || {};
      for (const k of Object.keys(pairs)) {
        const dt = document.createElement('dt');
        dt.textContent = String(k);
        const dd = document.createElement('dd');
        dd.textContent = String(pairs[k]);
        dl.appendChild(dt);
        dl.appendChild(dd);
      }
      return dl;
    }
    case 'link': {
      const a = document.createElement('a');
      const href = String(w.href || '');
      // Only allow http(s) links; anything else (javascript:, data:) is
      // rendered as inert text.
      if (/^https?:\/\//i.test(href)) {
        a.href = href;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.textContent = String(w.text || href);
        return a;
      }
      const span = document.createElement('span');
      span.textContent = String(w.text || href);
      return span;
    }
    case 'badge': {
      const span = document.createElement('span');
      span.className = 'plugin-panel-badge';
      span.textContent = String(w.text || '');
      return span;
    }
    default: {
      return document.createComment('unsupported widget');
    }
  }
}

// Convenience: fetch panels and append them into a container element.
export async function mountPluginPanels(container) {
  if (!container) return;
  const panels = await loadPluginPanels();
  container.replaceChildren();
  if (!panels.length) {
    const empty = document.createElement('p');
    empty.className = 'plugin-panel-empty';
    empty.textContent = 'No plugin panels.';
    container.appendChild(empty);
    return;
  }
  for (const panel of panels) {
    container.appendChild(renderPanel(panel));
  }
}

export default { loadPluginPanels, renderPanel, mountPluginPanels };
