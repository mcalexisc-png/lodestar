// Workspace switcher — multi-workspace support

let _workspaces = [];
let _activeId = '';

export async function loadWorkspaces() {
  try {
    const res = await fetch('/api/workspaces');
    if (!res.ok) return;
    const data = await res.json();
    _workspaces = data.workspaces || [];
    _activeId = data.active_id || '';
    _renderSwitcher();
  } catch (_) {}
}

async function _createWorkspace() {
  const name = prompt('Workspace name:');
  if (!name) return;
  const rootPath = prompt('Root path:');
  if (!rootPath) return;
  try {
    const res = await fetch('/api/workspaces', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, root_path: rootPath}),
    });
    if (!res.ok) {
      const text = await res.text();
      alert(`Error: ${text}`);
      return;
    }
    await loadWorkspaces();
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

async function _activateWorkspace(id) {
  try {
    const res = await fetch(`/api/workspaces/${id}/activate`, {method: 'POST'});
    if (!res.ok) {
      const text = await res.text();
      alert(`Error: ${text}`);
      return;
    }
    _activeId = id;
    _renderSwitcher();
    // Reload code workspace if open
    if (window.codeModule && window.codeModule.isCodeOpen()) {
      window.codeModule.closeCodeView();
      window.codeModule.openCodeView();
    }
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

async function _deleteWorkspace(id, name) {
  if (!confirm(`Delete workspace "${name}"?`)) return;
  try {
    await fetch(`/api/workspaces/${id}`, {method: 'DELETE'});
    await loadWorkspaces();
    if (window.codeModule && window.codeModule.isCodeOpen()) {
      window.codeModule.closeCodeView();
      window.codeModule.openCodeView();
    }
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

function _renderSwitcher() {
  const el = document.getElementById('workspace-switcher');
  if (!el) return;
  const active = _workspaces.find(w => w.id === _activeId);
  el.innerHTML = `
    <div class="workspace-current">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
      <span class="workspace-name" title="${_esc(active ? active.root_path : 'Default')}">${_esc(active ? active.name : 'Default')}</span>
    </div>
    <div class="workspace-list" id="workspace-list">
      ${_workspaces.map(w => `
        <div class="workspace-item ${w.id === _activeId ? 'active' : ''}" data-id="${w.id}">
          <span class="workspace-item-name">${_esc(w.name)}</span>
          <span class="workspace-item-path" title="${_esc(w.root_path)}">${_esc(w.root_path)}</span>
          <button class="workspace-item-del" data-id="${w.id}" data-name="${_esc(w.name)}" title="Delete workspace">&times;</button>
        </div>
      `).join('')}
      <div class="workspace-item workspace-add" id="workspace-add-btn">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        <span>New workspace</span>
      </div>
    </div>
  `;

  el.querySelectorAll('.workspace-item[data-id]').forEach(item => {
    item.addEventListener('click', e => {
      if (e.target.closest('.workspace-item-del')) return;
      _activateWorkspace(item.dataset.id);
    });
  });
  el.querySelectorAll('.workspace-item-del').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      _deleteWorkspace(btn.dataset.id, btn.dataset.name);
    });
  });
  document.getElementById('workspace-add-btn')?.addEventListener('click', _createWorkspace);
}

function _esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

const workspaceModule = {loadWorkspaces};
export default workspaceModule;
window.workspaceModule = workspaceModule;
