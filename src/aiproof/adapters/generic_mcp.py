"""Generic MCP installation for MCP-capable IDEs (read-only self-check)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aiproof.adapters.base import Adapter, Event, InstallResult, SupportLevel
from aiproof.adapters.registry import AGENTS, Agent, Support

# IDE id -> MCP config path (relative to home or project). VERIFY per vendor.
MCP_PRESETS: dict[str, str] = {
    "cursor": ".cursor/mcp.json",
    "cline": ".cline/mcp.json",
    "roo-code": ".roo/mcp.json",
    "continue": ".continue/config.json",
    "zed": ".config/zed/settings.json",
    "windsurf": ".codeium/windsurf/mcp_config.json",
    "vscode-copilot": ".vscode/mcp.json",
}

SERVER_NAME = "aiproof"


def mcp_server_entry() -> dict[str, Any]:
    """Return the standard stdio MCP server entry for AiProof."""
    return {"command": "aiproof", "args": ["mcp"]}


def mcp_snippet() -> dict[str, Any]:
    """Return a ready-to-merge MCP server config block."""
    return {"mcpServers": {SERVER_NAME: mcp_server_entry()}}


class McpAdapter(Adapter):
    """MCP-only adapter: registers the read-only AiProof MCP server."""

    id = "generic-mcp"
    support = SupportLevel.MCP_ONLY

    def detect(self, root: Path) -> bool:
        """Every MCP-capable environment is a candidate."""
        return (root / ".mcp.json").is_file()

    def install(self, root: Path, *, dry_run: bool = False) -> InstallResult:
        """Write/merge a project-level ``.mcp.json``."""
        path = root / ".mcp.json"
        result = InstallResult()
        raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        data: dict[str, Any] = raw if isinstance(raw, dict) else {}
        servers = data.get("mcpServers")
        if not isinstance(servers, dict):
            servers = {}
            data["mcpServers"] = servers
        servers.update(mcp_snippet()["mcpServers"])
        if dry_run:
            result.skipped.append(str(path))
            return result
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        result.changed.append(str(path))
        return result

    def uninstall(self, root: Path, *, dry_run: bool = False) -> InstallResult:
        """Remove the AiProof MCP entry."""
        path = root / ".mcp.json"
        result = InstallResult()
        if not path.is_file():
            return result
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        servers = data.get("mcpServers", {})
        if isinstance(servers, dict):
            servers.pop(SERVER_NAME, None)
        if dry_run:
            result.skipped.append(str(path))
            return result
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        result.changed.append(str(path))
        return result

    def parse_event(self, raw: dict[str, Any]) -> Event:
        """MCP servers do not emit lifecycle events."""
        return Event(name="", session_id="mcp", cwd=Path.cwd(), raw=raw)


def mcp_capable_agents() -> tuple[Agent, ...]:
    """Return registry agents that speak MCP."""
    return tuple(a for a in AGENTS if a.support in (Support.MCP_ONLY, Support.NATIVE_HOOKS))
