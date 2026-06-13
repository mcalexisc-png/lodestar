// static/js/hwfit_wizard.js — first-run hardware wizard
// Shows a one-time modal recommending lite vs full mode (and, for low-end
// hardware, a fast-cloud provider preset) based on services/hwfit detection.
// Advisory only: LODESTAR_LITE is read once at process start, so this never
// changes the running mode — it shows copy-paste instructions instead.

import { providerLogo } from './providers.js';

function el(id) { return document.getElementById(id); }

function escHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function renderResult(data) {
  const system = data.system || {};
  const specsEl = el('hwfit-wizard-specs');
  if (specsEl) {
    const parts = [];
    if (system.total_ram_gb != null) parts.push(`${system.total_ram_gb} GB RAM`);
    if (system.cpu_name) parts.push(system.cpu_name);
    parts.push(system.has_gpu ? (system.gpu_name || 'GPU detected') : 'No GPU detected');
    specsEl.textContent = parts.join(' · ');
  }

  const recEl = el('hwfit-wizard-recommendation');
  if (recEl) {
    const mode = data.recommend_mode === 'lite' ? 'Lite mode' : 'Full mode';
    recEl.innerHTML = `
      <h2 style="margin:0 0 6px;">Recommended: ${escHtml(mode)}</h2>
      <p style="margin:0;font-size:13px;opacity:0.85;">${escHtml(data.reason || '')}</p>
    `;
  }

  const applyEl = el('hwfit-wizard-apply');
  if (applyEl) {
    if (data.apply_lite) {
      applyEl.textContent = data.apply_lite;
      applyEl.classList.remove('hidden');
    } else {
      applyEl.classList.add('hidden');
    }
  }

  const providerWrap = el('hwfit-wizard-provider');
  const provider = data.recommend_provider;
  if (providerWrap) {
    if (provider) {
      const logoEl = el('hwfit-wizard-provider-logo');
      const nameEl = el('hwfit-wizard-provider-name');
      const urlEl = el('hwfit-wizard-provider-url');
      if (logoEl) logoEl.innerHTML = providerLogo(provider.logo) || '';
      if (nameEl) nameEl.textContent = provider.name || '';
      if (urlEl) urlEl.textContent = provider.base_url || '';
      providerWrap.classList.remove('hidden');

      const btn = el('hwfit-wizard-provider-btn');
      if (btn) {
        btn.onclick = () => {
          dismiss();
          const providerSel = el('adm-epProvider');
          const urlInput = el('adm-epUrl');
          if (providerSel && provider.base_url) {
            providerSel.value = provider.base_url;
            providerSel.dispatchEvent(new Event('change', { bubbles: true }));
          }
          if (urlInput && provider.base_url) urlInput.value = provider.base_url;
          if (window.adminModule && typeof window.adminModule.open === 'function') {
            window.adminModule.open('services');
          }
        };
      }
    } else {
      providerWrap.classList.add('hidden');
    }
  }
}

async function dismiss() {
  const modal = el('hwfit-wizard-modal');
  if (modal) modal.classList.add('hidden');
  try {
    await fetch('/api/hwfit/wizard-status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ completed: true }),
    });
  } catch (_) { /* best-effort */ }
}

async function show() {
  const modal = el('hwfit-wizard-modal');
  if (!modal) return;
  const loading = el('hwfit-wizard-loading');
  const result = el('hwfit-wizard-result');
  const errorEl = el('hwfit-wizard-error');
  if (loading) loading.classList.remove('hidden');
  if (result) result.classList.add('hidden');
  if (errorEl) errorEl.classList.add('hidden');
  modal.classList.remove('hidden');

  try {
    const res = await fetch('/api/hwfit/recommendation', { credentials: 'same-origin' });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || 'detection failed');
    renderResult(data);
    if (loading) loading.classList.add('hidden');
    if (result) result.classList.remove('hidden');
  } catch (_) {
    if (loading) loading.classList.add('hidden');
    if (errorEl) errorEl.classList.remove('hidden');
  }
}

function initEvents() {
  const closeBtn = el('hwfit-wizard-close');
  const dismissBtn = el('hwfit-wizard-dismiss');
  if (closeBtn) closeBtn.addEventListener('click', dismiss);
  if (dismissBtn) dismissBtn.addEventListener('click', dismiss);

  const rerunBtn = el('hwfit-wizard-rerun');
  if (rerunBtn) {
    rerunBtn.addEventListener('click', async () => {
      try {
        await fetch('/api/hwfit/wizard-status', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ completed: false }),
        });
      } catch (_) { /* best-effort */ }
      if (window.adminModule && typeof window.adminModule.close === 'function') {
        window.adminModule.close();
      }
      show();
    });
  }
}

async function maybeShowOnBoot() {
  try {
    const res = await fetch('/api/hwfit/wizard-status', { credentials: 'same-origin' });
    const data = await res.json();
    if (!data.completed) show();
  } catch (_) { /* best-effort */ }
}

document.addEventListener('DOMContentLoaded', () => {
  initEvents();
  maybeShowOnBoot();
});

const hwfitWizardModule = { show, dismiss };
export default hwfitWizardModule;
