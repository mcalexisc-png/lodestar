"""Bundled first-party Lodestar plugins (Tier 2, in-process).

Each subpackage exposes a ``manifest`` (a ``PluginManifest`` or a zero-arg
callable returning one). Discovered by ``src.plugins.loader``. Third-party
plugins are instead distributed as pip packages declaring a ``lodestar.tools``
entry point.
"""
