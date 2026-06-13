"""Plugin loader: entry-point discovery, enable/disable, lazy import, capability
enforcement.

Lifecycle (mirrors §4.3 of the planning doc):
  discover -> validate manifest -> register tool schema (cheap) ->
  on first call: enabled check -> capability check -> lazy import -> execute.

Discovery reads ``importlib.metadata`` entry points in the ``lodestar.tools``
group. Each entry point resolves to either a ``PluginManifest`` or a zero-arg
callable returning one. Resolving the entry point imports the *manifest*
module; the manifest's ``handler`` (a ``"module:attr"`` string or callable) is
only imported when the tool is first invoked, keeping unused plugins free at
startup.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import threading
from typing import Dict, List, Optional

from src.plugins.manifest import Capability, PluginManifest

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "lodestar.tools"


class PluginError(Exception):
    pass


class PluginLoader:
    """Discovers and runs in-process plugins."""

    def __init__(self, state_file: Optional[str] = None):
        self._manifests: Dict[str, PluginManifest] = {}
        self._handlers: Dict[str, object] = {}  # name -> resolved callable (lazy)
        self._enabled: Dict[str, bool] = {}
        self._loaded = False
        self._lock = threading.Lock()
        if state_file is None:
            try:
                from src.constants import DATA_DIR

                state_file = os.path.join(DATA_DIR, "plugins.json")
            except Exception:
                state_file = None
        self._state_file = state_file

    # ── discovery ────────────────────────────────────────────────────────────

    def discover(self, force: bool = False) -> None:
        """Discover plugins. Cheap: only manifests are read, never handlers.

        Two sources:
          1. ``importlib.metadata`` entry points in the ``lodestar.tools`` group
             (third-party, pip-installed plugins).
          2. The bundled ``plugins/`` directory in the repo (first-party
             plugins, discoverable when the app runs from source without a
             pip install).
        """
        with self._lock:
            if self._loaded and not force:
                return
            self._manifests.clear()
            self._handlers.clear()
            self._load_state()

            for ep in self._iter_entry_points():
                try:
                    obj = ep.load()
                    manifest = obj() if callable(obj) and not isinstance(obj, PluginManifest) else obj
                    self._register(manifest, source=f"entry-point:{ep.name}")
                except Exception as e:
                    logger.warning("failed to load plugin entry point %r: %s", getattr(ep, "name", "?"), e)

            for manifest, source in self._iter_bundled_manifests():
                try:
                    self._register(manifest, source=source)
                except Exception as e:
                    logger.warning("failed to register bundled plugin from %s: %s", source, e)

            self._loaded = True
            logger.info("Discovered %d in-process plugin(s): %s",
                        len(self._manifests), sorted(self._manifests))

    def _register(self, manifest, source: str) -> None:
        if not isinstance(manifest, PluginManifest):
            logger.warning("plugin source %s did not yield a PluginManifest", source)
            return
        manifest.validate()
        if manifest.name in self._manifests:
            logger.warning("duplicate plugin name %r (%s); keeping the first", manifest.name, source)
            return
        self._manifests[manifest.name] = manifest
        self._enabled.setdefault(manifest.name, True)

    @staticmethod
    def _iter_bundled_manifests():
        """Yield (manifest, source) for each package under the repo plugins/ dir.

        A bundled plugin is a package ``plugins/<pkg>/`` exposing a
        ``manifest`` attribute (a ``PluginManifest`` or a zero-arg callable
        returning one). Only the manifest module is imported here.
        """
        import importlib

        try:
            from src.constants import BASE_DIR

            plugins_dir = os.path.join(BASE_DIR, "plugins")
        except Exception:
            return
        if not os.path.isdir(plugins_dir):
            return
        for entry in sorted(os.listdir(plugins_dir)):
            pkg_dir = os.path.join(plugins_dir, entry)
            if not os.path.isdir(pkg_dir):
                continue
            if not os.path.exists(os.path.join(pkg_dir, "__init__.py")):
                continue
            mod_name = f"plugins.{entry}"
            try:
                module = importlib.import_module(mod_name)
                obj = getattr(module, "manifest", None)
                if obj is None:
                    continue
                manifest = obj() if callable(obj) else obj
                yield manifest, mod_name
            except Exception as e:
                logger.warning("bundled plugin %s failed to import its manifest: %s", mod_name, e)

    @staticmethod
    def _iter_entry_points():
        from importlib.metadata import entry_points

        try:
            eps = entry_points()
            # Python 3.10+ selectable API
            if hasattr(eps, "select"):
                return list(eps.select(group=ENTRY_POINT_GROUP))
            return list(eps.get(ENTRY_POINT_GROUP, []))  # pragma: no cover (old API)
        except Exception as e:
            logger.warning("entry-point discovery failed: %s", e)
            return []

    # ── enable/disable state ─────────────────────────────────────────────────

    def _load_state(self) -> None:
        self._enabled = {}
        if self._state_file and os.path.exists(self._state_file):
            try:
                with open(self._state_file, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._enabled = {k: bool(v) for k, v in (data.get("enabled") or {}).items()}
            except Exception as e:
                logger.warning("failed to read plugin state %s: %s", self._state_file, e)

    def _save_state(self) -> None:
        if not self._state_file:
            return
        try:
            os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
            tmp = self._state_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"enabled": self._enabled}, f, indent=2)
            os.replace(tmp, self._state_file)
        except Exception as e:
            logger.warning("failed to write plugin state %s: %s", self._state_file, e)

    def set_enabled(self, name: str, enabled: bool) -> None:
        self.discover()
        if name not in self._manifests:
            raise PluginError(f"unknown plugin: {name}")
        self._enabled[name] = enabled
        self._save_state()

    def is_enabled(self, name: str) -> bool:
        return self._enabled.get(name, True)

    # ── access ───────────────────────────────────────────────────────────────

    def list_plugins(self) -> List[Dict]:
        self.discover()
        out = []
        for name, manifest in sorted(self._manifests.items()):
            d = manifest.to_public_dict()
            d["enabled"] = self.is_enabled(name)
            out.append(d)
        return out

    def get_manifest(self, name: str) -> Optional[PluginManifest]:
        self.discover()
        return self._manifests.get(name)

    def enabled_manifests(self) -> List[PluginManifest]:
        self.discover()
        return [m for n, m in self._manifests.items() if self.is_enabled(n)]

    def tool_names(self) -> List[str]:
        return [m.name for m in self.enabled_manifests()]

    def tool_schemas(self) -> List[Dict]:
        return [m.to_tool_schema() for m in self.enabled_manifests()]

    def panels(self) -> List[Dict]:
        """Return sanitized UI panel specs for enabled plugins that define one."""
        out = []
        for m in self.enabled_manifests():
            panel = m.sanitized_panel()
            if panel:
                out.append(panel)
        return out

    # ── execution ────────────────────────────────────────────────────────────

    def _resolve_handler(self, manifest: PluginManifest):
        """Lazy-import the handler on first use."""
        if manifest.name in self._handlers:
            return self._handlers[manifest.name]
        handler = manifest.handler
        if isinstance(handler, str):
            if ":" not in handler:
                raise PluginError(f"plugin '{manifest.name}': handler must be 'module:attr'")
            mod_name, attr = handler.split(":", 1)
            module = importlib.import_module(mod_name)
            handler = getattr(module, attr)
        if not callable(handler):
            raise PluginError(f"plugin '{manifest.name}': handler is not callable")
        self._handlers[manifest.name] = handler
        return handler

    async def execute(self, name: str, content: str, ctx: Optional[Dict] = None) -> Dict:
        """Run a plugin tool by name with capability enforcement."""
        self.discover()
        manifest = self._manifests.get(name)
        if manifest is None:
            return {"error": f"Unknown plugin tool: {name}", "exit_code": 1}
        if not self.is_enabled(name):
            return {"error": f"Plugin '{name}' is disabled.", "exit_code": 1}

        ctx = dict(ctx or {})
        ctx["granted_capabilities"] = {c.value for c in manifest.capabilities}
        ctx["require_capability"] = _make_capability_guard(manifest)

        try:
            handler = self._resolve_handler(manifest)
        except Exception as e:
            logger.warning("plugin '%s' handler import failed: %s", name, e)
            return {"error": f"Plugin '{name}' failed to load: {e}", "exit_code": 1}

        try:
            result = handler(content, ctx)
            if hasattr(result, "__await__"):
                result = await result
            if not isinstance(result, dict):
                result = {"output": str(result), "exit_code": 0}
            return result
        except PermissionError as e:
            return {"error": f"Plugin '{name}' denied: {e}", "exit_code": 1}
        except Exception as e:
            logger.warning("plugin '%s' execution failed: %s", name, e)
            return {"error": f"Plugin '{name}' error: {e}", "exit_code": 1}


def _make_capability_guard(manifest: PluginManifest):
    """Return a guard the plugin (or host wrappers) call before a privileged op.

    ``ctx['require_capability']('net')`` raises PermissionError if the plugin did
    not declare that capability. This is best-effort host enforcement for
    trusted in-process tools; the strong isolation boundary remains MCP.
    """

    def guard(cap) -> None:
        cap_enum = cap if isinstance(cap, Capability) else Capability(str(cap))
        if not manifest.has_capability(cap_enum):
            raise PermissionError(
                f"plugin '{manifest.name}' did not declare the '{cap_enum.value}' capability"
            )

    return guard


_loader: Optional[PluginLoader] = None


def get_plugin_loader() -> PluginLoader:
    global _loader
    if _loader is None:
        _loader = PluginLoader()
    return _loader
