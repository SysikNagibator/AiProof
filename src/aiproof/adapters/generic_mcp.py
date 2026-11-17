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


def _read_json_object(path: Path) -> dict[str, Any] | None:
    """Read *path* as a JSON object.

    ``{}`` means "missing"; ``None`` means the file exists but cannot be trusted
    (invalid JSON or a non-object). Callers must never overwrite an untrusted file.
    """
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


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
        data = _read_json_object(path)
        if data is None:
            # Preserve an unparseable config instead of replacing it with a
            # partial object (same policy as the Claude Code adapter).
            result.skipped.append(str(path))
            return result
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
        data = _read_json_object(path)
        if data is None:
            result.skipped.append(str(path))
            return result
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
