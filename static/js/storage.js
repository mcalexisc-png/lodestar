// static/js/storage.js
// Centralized localStorage access with key constants and JSON parse safety

// TODO(lodestar): the KEYS below were renamed 'odysseus-*' -> 'lodestar-*'
// with a read/migrate fallback (see LEGACY_KEY_MAP + _migrateKey). Many
// other 'odysseus-*' localStorage keys, custom event names, and per-id key
// prefixes remain across static/js/* (calendar, notes, presets, sessions,
// models, document, email, compare, modalManager, etc.) — out of scope for
// this rebrand pass; a dedicated follow-up should sweep + decide per-key
// whether a migration fallback is warranted.

// ── Key constants ──
export const KEYS = {
  THEME: 'lodestar-theme',
  TOGGLES: 'lodestar-toggles',
  SIDEBAR_COLLAPSED: 'sidebar-collapsed',
  SIDEBAR_WIDTH: 'sidebar-width',
  SIDEBAR_SIDE: 'sidebar-side',
  CURRENT_SESSION: 'currentSessionId',
  COMPARE_SAVE: 'compare-save-results',
  COMPARE_CHAT: 'compare-continue-chat',
  COMPARE_BLIND: 'compare-blind',
  COMPARE_RANDOM: 'compare-randomize',
  MODELS_EXPANDED: 'lodestar-model-expanded',
  MODEL_ENDPOINTS: 'lodestar-model-endpoints',
  MODEL_SELECTED: 'lodestar-selected-model',
  SORT_ORDER: 'lodestar-sessions-sort',
  CHAT_SEARCH_SCOPE: 'lodestar-search-scope',
  INCOGNITO: 'lodestar-incognito',
  RAG_ACTIVE: 'lodestar-rag-active',
  MCP_ACTIVE: 'lodestar-mcp-active',
  SECTION_ORDER: 'sidebar-section-order',
  ADMIN_LAST_TAB: 'admin-last-tab',
  DENSITY: 'lodestar-density'
};

// Renamed 'odysseus-*' -> 'lodestar-*'. New writes go to the new key; reads
// fall back to the old key (one-time, via _migrateKey below) so existing
// users don't lose settings.
const LEGACY_KEY_MAP = {
  'lodestar-toggles': 'odysseus-toggles',
  'lodestar-model-expanded': 'odysseus-model-expanded',
  'lodestar-model-endpoints': 'odysseus-model-endpoints',
  'lodestar-selected-model': 'odysseus-selected-model',
  'lodestar-sessions-sort': 'odysseus-sessions-sort',
  'lodestar-search-scope': 'odysseus-search-scope',
  'lodestar-incognito': 'odysseus-incognito',
  'lodestar-rag-active': 'odysseus-rag-active',
  'lodestar-mcp-active': 'odysseus-mcp-active',
  'lodestar-density': 'odysseus-density',
  'lodestar-theme': 'odysseus-theme'
};

/**
 * Read a key, falling back to (and migrating from) its legacy 'odysseus-*'
 * name if the new key has never been written.
 */
function _migrateKey(key) {
  const legacy = LEGACY_KEY_MAP[key];
  if (!legacy) return;
  try {
    if (localStorage.getItem(key) === null) {
      const old = localStorage.getItem(legacy);
      if (old !== null) localStorage.setItem(key, old);
    }
  } catch (e) {
    // Ignore — getJSON/get below will just miss and use the fallback.
  }
}

/**
 * Safely get and parse a JSON value from localStorage.
 * Returns fallback on any error.
 */
export function getJSON(key, fallback) {
  _migrateKey(key);
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback !== undefined ? fallback : null;
    return JSON.parse(raw);
  } catch (e) {
    console.warn('[Storage] Failed to parse key "' + key + '":', e.message);
    return fallback !== undefined ? fallback : null;
  }
}

/**
 * Set a JSON-serialized value in localStorage.
 */
export function setJSON(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.warn('[Storage] Failed to set key "' + key + '":', e.message);
  }
}

/**
 * Get a raw string value from localStorage.
 */
export function get(key, fallback) {
  _migrateKey(key);
  try {
    const val = localStorage.getItem(key);
    return val !== null ? val : (fallback !== undefined ? fallback : null);
  } catch (e) {
    return fallback !== undefined ? fallback : null;
  }
}

/**
 * Set a raw string value in localStorage.
 */
export function set(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (e) {
    console.warn('[Storage] Failed to set key "' + key + '":', e.message);
  }
}

/**
 * Remove a key from localStorage.
 */
export function remove(key) {
  try {
    localStorage.removeItem(key);
  } catch (e) {
    // Ignore removal errors
  }
}

// ── Toggle state helpers ──

export function loadToggleState() {
  return getJSON(KEYS.TOGGLES, {});
}

export function saveToggleState(state) {
  setJSON(KEYS.TOGGLES, state);
}

export function getToggle(name, fallback) {
  const state = loadToggleState();
  return state[name] !== undefined ? state[name] : (fallback !== undefined ? fallback : false);
}

export function setToggle(name, value) {
  const state = loadToggleState();
  state[name] = value;
  saveToggleState(state);
}

const Storage = {
  KEYS,
  getJSON,
  setJSON,
  get,
  set,
  remove,
  loadToggleState,
  saveToggleState,
  getToggle,
  setToggle
};

export default Storage;
