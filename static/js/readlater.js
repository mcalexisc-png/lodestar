// Read Later — bookmark manager for web content

let _open = false;
let _items = [];
let _filter = '';

export function isOpen() { return _open; }

export function openPanel() {
  if (_open) return;
  _open = true;
  _renderPanel();
  _loadItems();
}

export function closePanel() {
  if (!_open) return;
  _open = false;
  const el = document.getElementById('readlater-panel');
  if (el) el.remove();
}

function _renderPanel() {
  let panel = document.getElementById('readlater-panel');
  if (panel) return;
  panel = document.createElement('div');
  panel.id = 'readlater-panel';
  panel.className = 'readlater-panel';
  panel.innerHTML = `
    <div class="readlater-header">
      <span>Read Later</span>
      <button class="readlater-close" id="readlater-close">&times;</button>
    </div>
    <div class="readlater-toolbar">
      <input class="readlater-search" id="readlater-search" placeholder="Search bookmarks..." />
      <button class="readlater-btn" id="readlater-add-btn">+ Add</button>
    </div>
    <div class="readlater-list" id="readlater-list">
      <div class="readlater-loading">Loading...</div>
    </div>
  `;
  document.body.appendChild(panel);
  panel.style.display = '';
  document.getElementById('readlater-close')?.addEventListener('click', closePanel);
  document.getElementById('readlater-add-btn')?.addEventListener('click', _showAddForm);
  document.getElementById('readlater-search')?.addEventListener('input', e => {
    _filter = e.target.value.trim();
    _renderList();
  });
}

async function _loadItems() {
  try {
    const res = await fetch('/api/read-later');
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    _items = data.items || [];
    _renderList();
  } catch (e) {
    const list = document.getElementById('readlater-list');
    if (list) list.innerHTML = `<div class="readlater-error">Error: ${_esc(e.message)}</div>`;
  }
}

function _renderList() {
  const list = document.getElementById('readlater-list');
  if (!list) return;
  let filtered = _items;
  if (_filter) {
    const q = _filter.toLowerCase();
    filtered = filtered.filter(i =>
      i.title.toLowerCase().includes(q) ||
      i.url.toLowerCase().includes(q) ||
      i.notes.toLowerCase().includes(q)
    );
  }
  list.innerHTML = filtered.map(i => `
    <div class="readlater-card ${i.is_read ? 'readlater-read' : ''}">
      <div class="readlater-card-header">
        <a class="readlater-card-title" href="${_esc(i.url)}" target="_blank" rel="noopener">${_esc(i.title || i.url)}</a>
      </div>
      <div class="readlater-card-url">${_esc(i.url)}</div>
      ${i.notes ? `<div class="readlater-card-notes">${_esc(i.notes)}</div>` : ''}
      <div class="readlater-card-actions">
        <button class="readlater-action" data-action="toggle" data-id="${i.id}">${i.is_read ? 'Unread' : 'Read'}</button>
        <button class="readlater-action" data-action="edit" data-id="${i.id}">Edit</button>
        <button class="readlater-action" data-action="delete" data-id="${i.id}">Delete</button>
      </div>
    </div>
  `).join('') || '<div class="readlater-empty">No bookmarks</div>';

  list.querySelectorAll('.readlater-action').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.id);
      const action = btn.dataset.action;
      if (action === 'toggle') _toggleRead(id);
      else if (action === 'edit') _editItem(id);
      else if (action === 'delete') _deleteItem(id);
    });
  });
}

function _showAddForm() {
  const list = document.getElementById('readlater-list');
  if (!list) return;
  list.innerHTML = `
    <div class="readlater-form">
      <input class="readlater-form-input" id="readlater-form-url" placeholder="URL" />
      <input class="readlater-form-input" id="readlater-form-title" placeholder="Title (optional)" />
      <textarea class="readlater-form-textarea" id="readlater-form-notes" placeholder="Notes (optional)" rows="3"></textarea>
      <div class="readlater-form-actions">
        <button class="readlater-btn" id="readlater-form-cancel">Cancel</button>
        <button class="readlater-btn readlater-btn-primary" id="readlater-form-save">Save</button>
      </div>
    </div>
  `;
  document.getElementById('readlater-form-cancel')?.addEventListener('click', _loadItems);
  document.getElementById('readlater-form-save')?.addEventListener('click', async () => {
    const url = document.getElementById('readlater-form-url').value.trim();
    if (!url) return;
    try {
      await fetch('/api/read-later', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          url,
          title: document.getElementById('readlater-form-title').value.trim(),
          notes: document.getElementById('readlater-form-notes').value.trim(),
        }),
      });
      _loadItems();
    } catch (e) { alert(`Error: ${e.message}`); }
  });
}

async function _toggleRead(id) {
  const item = _items.find(i => i.id === id);
  if (!item) return;
  try {
    await fetch(`/api/read-later/${id}`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({is_read: !item.is_read}),
    });
    _loadItems();
  } catch (e) { alert(`Error: ${e.message}`); }
}

async function _editItem(id) {
  const item = _items.find(i => i.id === id);
  if (!item) return;
  const list = document.getElementById('readlater-list');
  if (!list) return;
  list.innerHTML = `
    <div class="readlater-form">
      <input class="readlater-form-input" id="readlater-form-url" value="${_esc(item.url)}" />
      <input class="readlater-form-input" id="readlater-form-title" value="${_esc(item.title)}" />
      <textarea class="readlater-form-textarea" id="readlater-form-notes" rows="3">${_esc(item.notes)}</textarea>
      <label class="readlater-form-check"><input type="checkbox" id="readlater-form-read" ${item.is_read ? 'checked' : ''} /> Read</label>
      <div class="readlater-form-actions">
        <button class="readlater-btn" id="readlater-form-cancel">Cancel</button>
        <button class="readlater-btn readlater-btn-primary" id="readlater-form-save">Update</button>
      </div>
    </div>
  `;
  document.getElementById('readlater-form-cancel')?.addEventListener('click', _loadItems);
  document.getElementById('readlater-form-save')?.addEventListener('click', async () => {
    try {
      await fetch(`/api/read-later/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          url: document.getElementById('readlater-form-url').value.trim(),
          title: document.getElementById('readlater-form-title').value.trim(),
          notes: document.getElementById('readlater-form-notes').value.trim(),
          is_read: document.getElementById('readlater-form-read').checked,
        }),
      });
      _loadItems();
    } catch (e) { alert(`Error: ${e.message}`); }
  });
}

async function _deleteItem(id) {
  if (!confirm('Delete this bookmark?')) return;
  try {
    await fetch(`/api/read-later/${id}`, {method: 'DELETE'});
    _loadItems();
  } catch (e) { alert(`Error: ${e.message}`); }
}

function _esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

const readlaterModule = {openPanel, closePanel, isOpen};
export default readlaterModule;
window.readlaterModule = readlaterModule;
