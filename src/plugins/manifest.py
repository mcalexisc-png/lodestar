"""Plugin manifest + capability model.

A plugin is declared by a small object exposing four agent-readable fields plus
its required capabilities. The host reads the manifest cheaply at startup (no
plugin code imported) and only imports the plugin module on first invocation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class Capability(str, Enum):
    """Capabilities a plugin may declare and the host enforces.

    - ``NET``: the plugin makes network requests.
    - ``FS``: the plugin reads/writes the filesystem (within the host's path
      confinement; declaring FS does not bypass the deny/allow lists).
    - ``SHELL``: the plugin shells out to subprocesses.

    A plugin that does not declare a capability is denied that surface by the
    host (best-effort; the strong isolation boundary is MCP — see ADR 0004).
    """

    NET = "net"
    FS = "fs"
    SHELL = "shell"


@dataclass
class PluginManifest:
    """The four-field agent contract + capabilities + entry reference.

    ``name``        — unique tool name the agent calls (also the tool tag).
    ``when_to_use`` — one line telling the agent *when* to reach for this tool.
    ``how``         — one line on how to call it (expected input shape).
    ``tags``        — list of short tags for grouping/discovery.
    ``capabilities``— set of Capability the plugin needs.
    ``handler``     — an ``async (content, ctx) -> dict`` callable, or a dotted
                      ``"module:attr"`` import path resolved lazily on first use.
    ``parameters``  — optional JSON-schema ``properties`` dict for the function
                      schema shown to the LLM (defaults to a single ``input``
                      string).
    """

    name: str
    when_to_use: str
    how: str
    tags: List[str] = field(default_factory=list)
    capabilities: List[Capability] = field(default_factory=list)
    handler: Optional[Any] = None
    parameters: Optional[Dict[str, Any]] = None
    min_app_version: Optional[str] = None

    def validate(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise ValueError("plugin manifest: 'name' is required")
        if not self.when_to_use:
            raise ValueError(f"plugin '{self.name}': 'when_to_use' is required")
        if not self.how:
            raise ValueError(f"plugin '{self.name}': 'how' is required")
        # Normalize capabilities to the enum.
        norm: List[Capability] = []
        for cap in self.capabilities or []:
            norm.append(cap if isinstance(cap, Capability) else Capability(str(cap)))
        self.capabilities = norm

    def has_capability(self, cap: Capability) -> bool:
        return cap in (self.capabilities or [])

    def to_tool_schema(self) -> Dict[str, Any]:
        """Render an OpenAI-compatible function schema for the LLM.

        Uses the nested ``{"type": "function", "function": {...}}`` shape that
        matches ``src.tool_schemas.FUNCTION_TOOL_SCHEMAS``.
        """
        properties = self.parameters or {
            "input": {"type": "string", "description": self.how},
        }
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": f"{self.when_to_use} (how: {self.how})",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": list(properties.keys())[:1],
                },
            },
        }

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "when_to_use": self.when_to_use,
            "how": self.how,
            "tags": list(self.tags or []),
            "capabilities": [c.value for c in (self.capabilities or [])],
            "min_app_version": self.min_app_version,
        }
