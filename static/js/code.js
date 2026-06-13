// Code Workspace — file tree, CodeMirror 6 editor, tabs, git, execution, snippets
// Phase 2C: language extensions, exec button, tab persistence, keyboard shortcuts

let _open = false;
let _editorView = null;
let _editorStates = new Map();
let _activeFilePath = null;
let _fileTree = [];
let _currentDir = '';
let _cmLangLoaded = false;
let _langStream = null;
let _autoSaveTimer = null;
const SESSION_KEY = 'lodestar-code-tabs';

const API = '/api/code';

export function isCodeOpen() { return _open; }

export function openCodeView() {
  if (_open) return;
  _open = true;
  _renderUI();
  _loadLangModules();
  _loadFileTree('');
}

export function closeCodeView() {
  if (!_open) return;
  _open = false;
  _saveSession();
  const el = document.getElementById('code-workspace');
  if (el) el.remove();
  if (_editorView) { _editorView.destroy(); _editorView = null; }
  _editorStates.clear();
  _activeFilePath = null;
  document.getElementById('chat-container')?.classList.remove('code-active');
  window._restoreSidebarIfRouteCollapsed?.();
}

function _renderUI() {
  const container = document.getElementById('chat-container');
  if (!container) return;
  container.classList.add('code-active');

  const existing = document.getElementById('code-workspace');
  if (existing) existing.remove();

  const workspace = document.createElement('div');
  workspace.id = 'code-workspace';
  workspace.innerHTML = `
    <div class="code-layout">
      <div class="code-sidebar" id="code-sidebar">
        <div class="code-sidebar-header">
          <span class="code-sidebar-title">Files</span>
          <div class="code-sidebar-tabs">
            <button class="code-tab active" data-tab="files">Files</button>
            <button class="code-tab" data-tab="git">Git</button>
            <button class="code-tab" data-tab="snippets">Snippets</button>
          </div>
          <button class="code-idx-btn" id="code-index-btn" title="Index this project">Index</button>
        </div>
        <div class="code-tree" id="code-tree">
          <div class="code-tree-loading">Loading...</div>
        </div>
        <div class="code-git-panel" id="code-git-panel" style="display:none">
          <div class="code-git-loading">Loading git status...</div>
        </div>
        <div class="code-snippets-panel" id="code-snippets-panel" style="display:none">
          <div class="code-snippets-loading">Loading snippets...</div>
        </div>
      </div>
      <div class="code-main">
        <div class="code-tabs-bar" id="code-tabs-bar">
          <div class="code-tabs-empty">Open a file from the file tree</div>
          <div class="code-tabs-actions">
            <button class="code-action-btn" id="code-run-btn" title="Run Ctrl+Enter">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              Run
            </button>
            <button class="code-action-btn" id="code-save-btn" title="Save Ctrl+S">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
              Save
            </button>
            <label class="code-action-btn code-theme-toggle" title="Toggle theme">
              <input type="checkbox" id="code-editor-theme-toggle"
                ${document.body.classList.contains('dark') ? '' : 'checked'}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
            </label>
          </div>
        </div>
        <div class="code-editor-area" id="code-editor-area">
          <div class="code-editor-placeholder">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            <p>Select a file to edit</p>
          </div>
        </div>
        <div class="code-output" id="code-output" style="display:none">
          <div class="code-output-header">
            <span>Output</span>
            <div class="code-output-actions">
              <button class="code-output-action" id="code-output-copy">Copy</button>
              <button class="code-output-close" id="code-output-close">&times;</button>
            </div>
          </div>
          <pre class="code-output-body" id="code-output-body"></pre>
        </div>
      </div>
    </div>
  `;
  container.appendChild(workspace);

  document.getElementById('code-output-close')?.addEventListener('click', () => {
    document.getElementById('code-output').style.display = 'none';
  });
  document.getElementById('code-output-copy')?.addEventListener('click', () => {
    const body = document.getElementById('code-output-body');
    if (body) navigator.clipboard.writeText(body.textContent).catch(() => {});
  });

  document.querySelectorAll('.code-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.code-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const tabName = tab.dataset.tab;
      document.getElementById('code-tree').style.display = tabName === 'files' ? '' : 'none';
      document.getElementById('code-git-panel').style.display = tabName === 'git' ? '' : 'none';
      document.getElementById('code-snippets-panel').style.display = tabName === 'snippets' ? '' : 'none';
      if (tabName === 'git') _loadGitStatus();
      if (tabName === 'snippets') _loadSnippets();
    });
  });

  document.getElementById('code-index-btn')?.addEventListener('click', _indexProject);
  document.getElementById('code-run-btn')?.addEventListener('click', _runActiveFile);
  document.getElementById('code-save-btn')?.addEventListener('click', saveActiveFile);

  const themeToggle = document.getElementById('code-editor-theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('change', () => {
      if (_editorView) {
        _editorView.dispatch({});
        _recreateEditorView();
      }
    });
  }

  _restoreSession();
}

async function _loadLangModules() {
  if (_cmLangLoaded) return;
  try {
    const base = 'https://esm.sh/@codemirror/lang-';
    const langs = ['python', 'javascript', 'json', 'markdown', 'html', 'css', 'yaml', 'xml'];
    const promises = langs.map(name =>
      import(`${base}${name}@6.0.0`).catch(() => ({
        [`${name}Language`]: undefined, [`${name}`]: () => [],
      }))
    );
    _langStream = await Promise.all(promises);
    _cmLangLoaded = true;
  } catch (e) {
    console.warn('CodeMirror lang modules failed:', e);
  }
}

function _getLangExtension(lang) {
  if (!_langStream) return [];
  const map = {
    py: 0, python: 0,
    js: 1, javascript: 1, mjs: 1, cjs: 1,
    ts: 1, typescript: 1, tsx: 1,
    json: 2,
    md: 3, markdown: 3,
    html: 4, htm: 4,
    css: 5,
    yaml: 6, yml: 6,
    xml: 7, svg: 7,
  };
  const idx = map[lang];
  if (idx == null) return [];
  const mod = _langStream[idx];
  if (!mod) return [];
  const langFn = Object.values(mod).find(v => typeof v === 'function');
  if (!langFn) return [];
  try { return [langFn()]; } catch (_) { return []; }
}

function _loadFileTree(dir) {
  const treeEl = document.getElementById('code-tree');
  if (!treeEl) return;
  treeEl.innerHTML = '<div class="code-tree-loading">Loading...</div>';
  _currentDir = dir;
  const params = dir ? `?root=${encodeURIComponent(dir)}` : '';
  fetch(`${API}/files${params}`)
    .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
    .then(data => {
      _fileTree = data.entries || [];
      _renderTree(treeEl, _fileTree);
    })
    .catch(e => { treeEl.innerHTML = `<div class="code-tree-error">Error: ${e.message}</div>`; });
}

function _renderTree(container, entries) {
  if (!entries.length) {
    container.innerHTML = '<div class="code-tree-empty">Empty directory</div>';
    return;
  }
  container.innerHTML = entries.map(e => `
    <div class="code-tree-item ${e.is_dir ? 'code-tree-dir' : 'code-tree-file'}"
         data-path="${_esc(e.path)}" data-isdir="${e.is_dir}">
      ${e.is_dir
        ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>'
        : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>'}
      <span class="code-tree-name">${_esc(e.name)}</span>
    </div>
  `).join('');

  container.querySelectorAll('.code-tree-dir').forEach(el => {
    el.addEventListener('click', () => _loadFileTree(el.dataset.path));
  });
  container.querySelectorAll('.code-tree-file').forEach(el => {
    el.addEventListener('click', () => _openFileInTab(el.dataset.path));
  });
}

function _openFileInTab(path) {
  const bar = document.getElementById('code-tabs-bar');
  if (!bar) return;
  const existingTab = bar.querySelector(`.code-tab-item[data-path="${_esc(path)}"]`);
  if (existingTab) {
    existingTab.click();
    _activateTab(path);
    return;
  }
  _addTab(path);
  _loadTabContent(path);
  _saveSession();
}

function _addTab(path) {
  const bar = document.getElementById('code-tabs-bar');
  if (!bar) return;
  const placeholder = bar.querySelector('.code-tabs-empty');
  if (placeholder) placeholder.remove();
  const name = path.split('/').pop() || path;
  const tab = document.createElement('div');
  tab.className = 'code-tab-item active';
  tab.dataset.path = path;
  tab.innerHTML = `
    <span class="code-tab-label">${_esc(name)}</span>
    <span class="code-tab-close">&times;</span>
  `;
  tab.addEventListener('click', () => _activateTab(path));
  tab.querySelector('.code-tab-close').addEventListener('click', e => {
    e.stopPropagation();
    _closeTab(path);
  });
  bar.prepend(tab);
}

function _activateTab(path) {
  document.querySelectorAll('.code-tab-item').forEach(t => t.classList.remove('active'));
  const tab = document.querySelector(`.code-tab-item[data-path="${_esc(path)}"]`);
  if (tab) tab.classList.add('active');
  _activeFilePath = path;
  const state = _editorStates.get(path);
  if (state) {
    _loadCodeMirror(state.content, state.language, state.scroll);
  } else {
    _loadTabContent(path);
  }
}

function _loadTabContent(path) {
  fetch(`${API}/file?path=${encodeURIComponent(path)}`)
    .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
    .then(data => {
      _activeFilePath = data.path;
      const ext = data.language || 'plaintext';
      _loadCodeMirror(data.content, ext);
      _editorStates.set(data.path, {content: data.content, language: ext, scroll: 0});
    })
    .catch(e => _showOutput('Error', `Failed to open file: ${e.message}`));
}

function _closeTab(path) {
  const tab = document.querySelector(`.code-tab-item[data-path="${_esc(path)}"]`);
  if (tab) tab.remove();
  _editorStates.delete(path);
  if (_activeFilePath === path) {
    _activeFilePath = null;
    const firstTab = document.querySelector('.code-tab-item');
    if (firstTab) {
      firstTab.click();
      _activateTab(firstTab.dataset.path);
    } else {
      _clearEditor();
      const bar = document.getElementById('code-tabs-bar');
      if (bar && !bar.querySelector('.code-tab-item')) {
        const placeholder = document.createElement('div');
        placeholder.className = 'code-tabs-empty';
        placeholder.textContent = 'Open a file from the file tree';
        bar.querySelector('.code-tabs-actions')?.before(placeholder);
      }
    }
  }
  _saveSession();
}

function _clearEditor() {
  const area = document.getElementById('code-editor-area');
  if (!area) return;
  if (_editorView) { _editorView.destroy(); _editorView = null; }
  area.innerHTML = `<div class="code-editor-placeholder">
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
    <p>Select a file to edit</p>
  </div>`;
}

function _loadCodeMirror(content, language, scrollPos) {
  const area = document.getElementById('code-editor-area');
  if (!area) return;

  _getCodeMirror().then(cm => {
    const langExt = _getLangExtension(language);
    const themeExt = _getThemeExtension(cm);

    if (_editorView) {
      _editorView.dispatch({
        changes: {from: 0, to: _editorView.state.doc.length, insert: content},
        effects: cm.StateEffect.reconfigure.of([cm.basicSetup, langExt, themeExt, cm.EditorView.lineWrapping, _editorUpdates()].flat()),
      });
      if (scrollPos != null) _editorView.scrollDOM.scrollTop = scrollPos;
      return;
    }

    area.innerHTML = '';
    const editorDiv = document.createElement('div');
    editorDiv.id = 'code-cm-editor';
    area.appendChild(editorDiv);

    _editorView = new cm.EditorView({
      state: cm.EditorState.create({
        doc: content,
        extensions: [cm.basicSetup, langExt, themeExt, cm.EditorView.lineWrapping, _editorUpdates()].flat(),
      }),
      parent: editorDiv,
    });
  }).catch(() => {
    area.innerHTML = `<div class="code-editor-fallback">
      <textarea style="width:100%;height:100%;min-height:300px;font-family:monospace;font-size:13px;padding:8px;">${_esc(content)}</textarea>
    </div>`;
  });
}

function _recreateEditorView() {
  const area = document.getElementById('code-editor-area');
  if (!area || !_editorView) return;
  const content = _editorView.state.doc.toString();
  const scroll = _editorView.scrollDOM.scrollTop;
  const path = _activeFilePath;
  const state = _editorStates.get(path);
  const lang = state ? state.language : 'plaintext';
  _editorView.destroy();
  _editorView = null;
  _loadCodeMirror(content, lang, scroll);
}

function _editorUpdates() {
  const {EditorView} = window.__cmExports || {};
  if (!EditorView) return [];
  return EditorView.updateListener.of(update => {
    if (update.docChanged && _activeFilePath) {
      const content = update.state.doc.toString();
      const state = _editorStates.get(_activeFilePath);
      if (state) {
        state.content = content;
        state.scroll = _editorView ? _editorView.scrollDOM.scrollTop : 0;
      }
      document.querySelector('.code-tab-item.active')?.classList.add('dirty');
      _scheduleAutoSave(_activeFilePath, content);
    }
  });
}

function _scheduleAutoSave(path, content) {
  if (_autoSaveTimer) clearTimeout(_autoSaveTimer);
  _autoSaveTimer = setTimeout(() => {
    fetch(`${API}/file`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({path, content}),
    }).then(r => {
      if (r.ok) document.querySelector('.code-tab-item.active')?.classList.remove('dirty');
    }).catch(() => {});
  }, 2000);
}

function _getThemeExtension(cm) {
  const lightMode = document.getElementById('code-editor-theme-toggle')?.checked;
  if (!cm.EditorView) return [];
  const bg = lightMode ? '#ffffff' : '#1e1e1e';
  const fg = lightMode ? '#1e1e1e' : '#d4d4d4';
  const gutterBg = lightMode ? '#f5f5f5' : '#252526';
  const gutterFg = lightMode ? '#999' : '#858585';
  const activeBg = lightMode ? '#e8f2ff44' : '#2a2d2e44';
  const selBg = lightMode ? '#add6ff44' : '#264f7844';
  return cm.EditorView.theme({
    '&': {backgroundColor: bg, color: fg, height: '100%'},
    '.cm-content': {fontFamily: '"Fira Code", "Cascadia Code", "JetBrains Mono", monospace', fontSize: '13px', padding: '4px 0'},
    '.cm-gutters': {backgroundColor: gutterBg, color: gutterFg, border: 'none'},
    '.cm-activeLineGutter': {backgroundColor: lightMode ? '#e8f2ff' : '#2a2d2e'},
    '.cm-activeLine': {backgroundColor: activeBg},
    '.cm-cursor': {borderLeftColor: lightMode ? '#000' : '#aeafad'},
    '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': {backgroundColor: selBg},
    '.cm-matchingBracket': {backgroundColor: colorMix(selBg, 0.3), outline: `1px solid ${lightMode ? '#999' : '#666'}`},
  });
}

function colorMix(color, alpha) {
  return color.replace(/[\d.]+\)$/, a => (parseFloat(a) * alpha) + ')');
}

let _cmPromise = null;
function _getCodeMirror() {
  if (!_cmPromise) {
    _cmPromise = import('https://esm.sh/@codemirror/basic-setup@6.0.0').then(m => {
      window.__cmExports = m;
      return m;
    }).catch(() => {
      return import('https://cdn.jsdelivr.net/npm/@codemirror/basic-setup@6.0.0/dist/index.js').then(m => {
        window.__cmExports = m;
        return m;
      });
    });
  }
  return _cmPromise;
}

function _showOutput(title, text) {
  const panel = document.getElementById('code-output');
  const body = document.getElementById('code-output-body');
  if (!panel || !body) return;
  const prefix = title ? `${title}:\n` : '';
  body.textContent = prefix + text;
  panel.style.display = '';
}

function _runActiveFile() {
  const path = _activeFilePath;
  if (!path) return _showOutput('Run', 'Open a file first');
  if (!_editorView) return _showOutput('Run', 'No active editor');

  const content = _editorView.state.doc.toString();
  const ext = path.split('.').pop() || '';

  _showOutput('Run', 'Running...');

  fetch(`${API}/run`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({file_path: path, language: ext, stdin_input: ''}),
  })
    .then(r => {
      if (!r.ok) return r.text().then(t => { throw new Error(t); });
      return r.json();
    })
    .then(data => {
      let out = '';
      if (data.stdout) out += data.stdout;
      if (data.stderr) out += (out ? '\n' : '') + data.stderr;
      if (!out) out = data.exit_code === 0 ? '(no output)' : `(exit ${data.exit_code})`;
      _showOutput('Run', out);
    })
    .catch(e => _showOutput('Run', e.message));
}

function _showNewSnippetDialog() {
  const name = prompt('Snippet name:');
  if (!name) return;
  const body = prompt('Snippet body:');
  if (!body) return;
  fetch(`${API}/snippets`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, body}),
  }).then(() => _loadSnippets()).catch(e => _showOutput('Snippets', e.message));
}

async function _loadGitStatus() {
  const panel = document.getElementById('code-git-panel');
  if (!panel) return;
  panel.innerHTML = '<div class="code-git-loading">Loading...</div>';
  try {
    const res = await fetch(`${API}/git/status`);
    if (!res.ok) throw new Error('Git panel requires a git repo in the workspace root');
    const data = await res.json();
    panel.innerHTML = _renderGitStatus(data);
    _wireGitButtons();
  } catch (e) {
    panel.innerHTML = `<div class="code-tree-error">${_esc(e.message)}</div>`;
  }
}

function _renderGitStatus(data) {
  const files = (data.files || []).map(f =>
    `<div class="code-git-file">
      <span class="code-git-status code-git-${f.status}">${_esc(f.status)}</span>
      <span class="code-git-path">${_esc(f.path)}</span>
    </div>`
  ).join('');
  const commits = (data.log || []).map(c =>
    `<div class="code-git-commit">
      <span class="code-git-hash">${_esc(c.hash.slice(0, 7))}</span>
      <span class="code-git-msg">${_esc(c.message)}</span>
    </div>`
  ).join('');
  return `
    <div class="code-git-branch"><strong>Branch:</strong> ${_esc(data.branch)}</div>
    <div class="code-git-files">${files || '<em>No changes</em>'}</div>
    <div class="code-git-actions">
      <input class="code-git-commit-input" id="code-git-commit-input" placeholder="Commit message" />
      <button class="code-git-btn" id="code-git-commit-btn">Commit</button>
      <button class="code-git-btn" id="code-git-ai-msg-btn">AI message</button>
    </div>
    <div class="code-git-log"><strong>Recent commits:</strong>${commits || '<em>None</em>'}</div>
  `;
}

function _wireGitButtons() {
  document.getElementById('code-git-commit-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('code-git-commit-input');
    if (!input || !input.value.trim()) return;
    try {
      const res = await fetch(`${API}/git/commit`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: input.value.trim()}),
      });
      const data = await res.json();
      if (data.ok) {
        input.value = '';
        _loadGitStatus();
      }
    } catch (e) {
      _showOutput('Git', e.message);
    }
  });
  document.getElementById('code-git-ai-msg-btn')?.addEventListener('click', async () => {
    try {
      const res = await fetch(`${API}/git/ai-commit-msg`);
      const data = await res.json();
      const input = document.getElementById('code-git-commit-input');
      if (input) input.value = data.message || '';
    } catch (e) {
      _showOutput('Git', e.message);
    }
  });
}

async function _loadSnippets() {
  const panel = document.getElementById('code-snippets-panel');
  if (!panel) return;
  panel.innerHTML = '<div class="code-snippets-loading">Loading...</div>';
  try {
    const res = await fetch(`${API}/snippets`);
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    panel.innerHTML = _renderSnippets(data.snippets || []);
    _wireSnippetButtons();
  } catch (e) {
    panel.innerHTML = `<div class="code-tree-error">${_esc(e.message)}</div>`;
  }
}

function _renderSnippets(snippets) {
  const items = snippets.map(s =>
    `<div class="code-snippet-item" data-id="${s.id}">
      <div class="code-snippet-name">${_esc(s.name)}</div>
      <div class="code-snippet-lang">${_esc(s.language || '')}</div>
      <pre class="code-snippet-body">${_esc(s.body.slice(0, 200))}</pre>
    </div>`
  ).join('');
  return `
    <div class="code-snippets-toolbar">
      <button class="code-git-btn" id="code-snippet-new-btn">+ New snippet</button>
    </div>
    <div class="code-snippets-list">${items || '<em>No snippets yet</em>'}</div>
  `;
}

function _wireSnippetButtons() {
  document.getElementById('code-snippet-new-btn')?.addEventListener('click', _showNewSnippetDialog);
}

async function _indexProject() {
  try {
    const res = await fetch(`${API}/index`, {method: 'POST'});
    const data = await res.json();
    _showOutput('Index', data.message || 'Indexing complete');
  } catch (e) {
    _showOutput('Index', e.message);
  }
}

// ── Tab persistence ──

function _saveSession() {
  try {
    const bar = document.getElementById('code-tabs-bar');
    if (!bar) return;
    const tabs = [...bar.querySelectorAll('.code-tab-item')].map(t => t.dataset.path).filter(Boolean);
    const active = _activeFilePath;
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({tabs, active}));
  } catch (_) {}
}

function _restoreSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return;
    const {tabs, active} = JSON.parse(raw);
    if (!tabs || !tabs.length) return;
    tabs.forEach(path => _addTab(path));
    if (active && tabs.includes(active)) {
      _activateTab(active);
    } else {
      const first = document.querySelector('.code-tab-item');
      if (first) _activateTab(first.dataset.path);
    }
  } catch (_) {}
}

// ── Keyboard shortcuts ──

document.addEventListener('keydown', e => {
  if (!_open || !_editorView) return;
  const mod = e.metaKey || e.ctrlKey;
  if (mod && e.key === 's') {
    e.preventDefault();
    saveActiveFile();
  }
  if (mod && e.key === 'Enter') {
    e.preventDefault();
    _runActiveFile();
  }
});

// ── Public API ──

export async function saveActiveFile() {
  if (!_activeFilePath || !_editorView) return;
  const content = _editorView.state.doc.toString();
  try {
    const r = await fetch(`${API}/file`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({path: _activeFilePath, content}),
    });
    if (r.ok) {
      document.querySelector('.code-tab-item.active')?.classList.remove('dirty');
      return true;
    }
  } catch (_) {}
  return false;
}

function _esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

const codeModule = {openCodeView, closeCodeView, isCodeOpen, saveActiveFile};
export default codeModule;
window.codeModule = codeModule;
