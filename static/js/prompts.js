// Prompt Library — browse, search, create, edit, and insert prompts

let _open = false;
let _prompts = [];
let _categories = [];
let _filterCat = '';
let _filterSearch = '';

export function isOpen() { return _open; }

export function openPanel() {
  if (_open) return;
  _open = true;
  _renderPanel();
  _loadPrompts();
}

export function closePanel() {
  if (!_open) return;
  _open = false;
  const el = document.getElementById('prompt-library-panel');
  if (el) el.remove();
}

function _renderPanel() {
  let panel = document.getElementById('prompt-library-panel');
  if (panel) return;
  panel = document.createElement('div');
  panel.id = 'prompt-library-panel';
  panel.className = 'prompt-panel';
  panel.innerHTML = `
    <div class="prompt-panel-header">
      <span>Prompt Library</span>
      <button class="prompt-panel-close" id="prompt-panel-close">&times;</button>
    </div>
    <div class="prompt-panel-toolbar">
      <input class="prompt-search" id="prompt-search" placeholder="Search prompts..." />
      <select class="prompt-cat-select" id="prompt-cat-select">
        <option value="">All categories</option>
      </select>
      <button class="prompt-btn" id="prompt-new-btn">+ New</button>
    </div>
    <div class="prompt-list" id="prompt-list">
      <div class="prompt-loading">Loading...</div>
    </div>
  `;
  document.body.appendChild(panel);
  panel.style.display = '';

  document.getElementById('prompt-panel-close')?.addEventListener('click', closePanel);
  document.getElementById('prompt-new-btn')?.addEventListener('click', _showForm);
  document.getElementById('prompt-search')?.addEventListener('input', e => {
    _filterSearch = e.target.value.trim();
    _renderList();
  });
  document.getElementById('prompt-cat-select')?.addEventListener('change', e => {
    _filterCat = e.target.value;
    _renderList();
  });
}

async function _loadPrompts() {
  try {
    const [pRes, cRes] = await Promise.all([
      fetch('/api/prompts'),
      fetch('/api/prompts/categories'),
    ]);
    const pData = await pRes.json();
    const cData = await cRes.json();
    _prompts = pData.prompts || [];
    _categories = cData.categories || [];
    _populateCategories();
    _renderList();
  } catch (e) {
    const list = document.getElementById('prompt-list');
    if (list) list.innerHTML = `<div class="prompt-error">Error: ${_esc(e.message)}</div>`;
  }
}

function _populateCategories() {
  const sel = document.getElementById('prompt-cat-select');
  if (!sel) return;
  sel.innerHTML = '<option value="">All categories</option>' +
    _categories.map(c => `<option value="${_esc(c)}">${_esc(c)}</option>`).join('');
}

function _renderList() {
  const list = document.getElementById('prompt-list');
  if (!list) return;
  let filtered = _prompts;
  if (_filterCat) filtered = filtered.filter(p => p.category === _filterCat);
  if (_filterSearch) {
    const q = _filterSearch.toLowerCase();
    filtered = filtered.filter(p =>
      p.name.toLowerCase().includes(q) ||
      p.description.toLowerCase().includes(q) ||
      p.body.toLowerCase().includes(q)
    );
  }
  list.innerHTML = filtered.map(p => `
    <div class="prompt-card" data-id="${p.id}">
      <div class="prompt-card-header">
        <span class="prompt-card-name">${_esc(p.name)}</span>
        ${p.category ? `<span class="prompt-card-cat">${_esc(p.category)}</span>` : ''}
      </div>
      ${p.description ? `<div class="prompt-card-desc">${_esc(p.description)}</div>` : ''}
      <pre class="prompt-card-body">${_esc(_truncate(p.body, 150))}</pre>
      <div class="prompt-card-actions">
        <button class="prompt-action" data-action="insert" data-id="${p.id}">Insert</button>
        <button class="prompt-action" data-action="edit" data-id="${p.id}">Edit</button>
        <button class="prompt-action" data-action="delete" data-id="${p.id}">Delete</button>
      </div>
    </div>
  `).join('') || '<div class="prompt-empty">No prompts found</div>';

  list.querySelectorAll('.prompt-action').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.id);
      const action = btn.dataset.action;
      if (action === 'insert') _insertPrompt(id);
      else if (action === 'edit') _editPrompt(id);
      else if (action === 'delete') _deletePrompt(id);
    });
  });
}

function _showForm(editData) {
  const list = document.getElementById('prompt-list');
  if (!list) return;
  const d = editData || {};
  list.innerHTML = `
    <div class="prompt-form">
      <input class="prompt-form-input" id="prompt-form-name" placeholder="Name" value="${_esc(d.name || '')}" />
      <input class="prompt-form-input" id="prompt-form-desc" placeholder="Description (optional)" value="${_esc(d.description || '')}" />
      <input class="prompt-form-input" id="prompt-form-cat" placeholder="Category (optional)" value="${_esc(d.category || '')}" />
      <textarea class="prompt-form-textarea" id="prompt-form-body" placeholder="Prompt body..." rows="6">${_esc(d.body || '')}</textarea>
      <input class="prompt-form-input" id="prompt-form-tags" placeholder="Tags (comma-separated)" value="${_esc((d.tags || []).join(', '))}" />
      <div class="prompt-form-actions">
        <button class="prompt-btn" id="prompt-form-cancel">Cancel</button>
        <button class="prompt-btn prompt-btn-primary" id="prompt-form-save">${d.id ? 'Update' : 'Save'}</button>
      </div>
    </div>
  `;
  document.getElementById('prompt-form-cancel')?.addEventListener('click', _loadPrompts);
  document.getElementById('prompt-form-save')?.addEventListener('click', async () => {
    const name = document.getElementById('prompt-form-name').value.trim();
    const body = document.getElementById('prompt-form-body').value.trim();
    if (!name || !body) return;
    const payload = {
      name,
      body,
      description: document.getElementById('prompt-form-desc').value.trim(),
      category: document.getElementById('prompt-form-cat').value.trim(),
      tags: document.getElementById('prompt-form-tags').value.split(',').map(s => s.trim()).filter(Boolean),
    };
    try {
      if (d.id) {
        await fetch(`/api/prompts/${d.id}`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
      } else {
        await fetch('/api/prompts', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
      }
      _loadPrompts();
    } catch (e) {
      alert(`Error: ${e.message}`);
    }
  });
}

async function _insertPrompt(id) {
  const prompt = _prompts.find(p => p.id === id);
  if (!prompt) return;
  // Insert into the chat input
  const textarea = document.querySelector('.chat-input-area textarea, .chat-input');
  if (textarea) {
    textarea.focus();
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    textarea.value = textarea.value.slice(0, start) + prompt.body + textarea.value.slice(end);
    textarea.selectionStart = textarea.selectionEnd = start + prompt.body.length;
    textarea.dispatchEvent(new Event('input', {bubbles: true}));
  } else {
    navigator.clipboard.writeText(prompt.body).catch(() => {});
  }
}

async function _editPrompt(id) {
  const prompt = _prompts.find(p => p.id === id);
  if (prompt) _showForm(prompt);
}

async function _deletePrompt(id) {
  if (!confirm('Delete this prompt?')) return;
  try {
    await fetch(`/api/prompts/${id}`, {method: 'DELETE'});
    _loadPrompts();
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

function _truncate(s, max) {
  return s.length > max ? s.slice(0, max) + '…' : s;
}

function _esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

const promptModule = {openPanel, closePanel, isOpen};
export default promptModule;
window.promptModule = promptModule;
