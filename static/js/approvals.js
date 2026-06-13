// Agent Approval — review and approve/reject tool call requests

let _open = false;
let _approvals = [];

export function isOpen() { return _open; }

export function openPanel() {
  if (_open) return;
  _open = true;
  _renderPanel();
  _loadApprovals();
}

export function closePanel() {
  if (!_open) return;
  _open = false;
  const el = document.getElementById('approval-panel');
  if (el) el.remove();
}

function _renderPanel() {
  let panel = document.getElementById('approval-panel');
  if (panel) return;
  panel = document.createElement('div');
  panel.id = 'approval-panel';
  panel.className = 'approval-panel';
  panel.innerHTML = `
    <div class="approval-header">
      <span>Agent Approvals</span>
      <button class="approval-close" id="approval-close">&times;</button>
    </div>
    <div class="approval-list" id="approval-list">
      <div class="approval-loading">Loading...</div>
    </div>
  `;
  document.body.appendChild(panel);
  panel.style.display = '';
  document.getElementById('approval-close')?.addEventListener('click', closePanel);
}

async function _loadApprovals() {
  try {
    const res = await fetch('/api/approvals');
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    _approvals = data.approvals || [];
    _renderList();
  } catch (e) {
    const list = document.getElementById('approval-list');
    if (list) list.innerHTML = `<div class="approval-error">Error: ${_esc(e.message)}</div>`;
  }
}

function _renderList() {
  const list = document.getElementById('approval-list');
  if (!list) return;
  list.innerHTML = _approvals.map(a => `
    <div class="approval-card approval-${a.status}">
      <div class="approval-card-header">
        <span class="approval-tool">${_esc(a.tool_name)}</span>
        <span class="approval-status badge-${a.status}">${a.status}</span>
      </div>
      ${a.explanation ? `<div class="approval-explanation">${_esc(a.explanation)}</div>` : ''}
      ${a.tool_args ? `<pre class="approval-args">${_esc(_truncate(a.tool_args, 300))}</pre>` : ''}
      ${a.status === 'pending' ? `
        <div class="approval-actions">
          <button class="approval-btn approval-btn-approve" data-id="${a.id}">Approve</button>
          <button class="approval-btn approval-btn-reject" data-id="${a.id}">Reject</button>
        </div>
      ` : `
        <div class="approval-resolved">${a.resolved_at ? _esc(new Date(a.resolved_at).toLocaleString()) : ''}</div>
      `}
    </div>
  `).join('') || '<div class="approval-empty">No approvals</div>';

  list.querySelectorAll('.approval-btn-approve').forEach(btn => {
    btn.addEventListener('click', () => _resolve(btn.dataset.id, 'approve'));
  });
  list.querySelectorAll('.approval-btn-reject').forEach(btn => {
    btn.addEventListener('click', () => _resolve(btn.dataset.id, 'reject'));
  });
}

async function _resolve(id, action) {
  try {
    const res = await fetch(`/api/approvals/${id}/${action}`, {method: 'POST'});
    if (!res.ok) throw new Error(await res.text());
    _loadApprovals();
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

const approvalModule = {openPanel, closePanel, isOpen};
export default approvalModule;
window.approvalModule = approvalModule;
