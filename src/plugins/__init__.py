"""In-process, lightweight Lodestar plugins (Tier 2 of the plugin system).

Discovered via ``importlib.metadata`` entry points in the ``lodestar.tools``
group. Each plugin ships a four-field manifest (``name``, ``when_to_use``,
``how``, ``tags``), declares the capabilities it needs (``net``/``fs``/
``shell``), and is **lazy-imported on first use** — an installed-but-unused
plugin costs nothing at startup beyond reading its manifest.

This tier is for small, trusted, pure-Python tools only. Anything heavy,
third-party, or untrusted should ship as an MCP server (see ADR 0004), which
runs out-of-process and can't OOM or crash the host.
"""

from src.plugins.manifest import PluginManifest, Capability
from src.plugins.loader import (
    PluginLoader,
    get_plugin_loader,
)

__all__ = [
    "PluginManifest",
    "Capability",
    "PluginLoader",
    "get_plugin_loader",
]
