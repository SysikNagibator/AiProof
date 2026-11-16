"""Adapters: Claude Code hooks install/uninstall/parse; MCP registration."""

from __future__ import annotations

import json
from pathlib import Path

from aiproof.adapters import adapter, detect_all
from aiproof.adapters.claude_code import ClaudeCodeAdapter
from aiproof.adapters.generic_mcp import McpAdapter, mcp_snippet


def test_claude_install_writes_hooks(tmp_path: Path) -> None:
    result = ClaudeCodeAdapter().install(tmp_path)
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    assert "hooks" in settings
    assert set(settings["hooks"]) >= {"SessionStart", "PreToolUse", "PostToolUse", "Stop"}
    assert result.changed


def test_claude_install_idempotent(tmp_path: Path) -> None:
    adapter_ = ClaudeCodeAdapter()
    adapter_.install(tmp_path)
    adapter_.install(tmp_path)
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    stop_groups = settings["hooks"]["Stop"]
    ours = [h for g in stop_groups for h in g.get("hooks", []) if "aiproof hook" in h["command"]]
    assert len(ours) == 1


def test_claude_uninstall_removes_only_ours(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "user-script"}]}]}}
        )
    )
    ClaudeCodeAdapter().install(tmp_path)
    ClaudeCodeAdapter().uninstall(tmp_path)
    remaining = json.loads(settings_path.read_text())
    flat = [h for g in remaining.get("hooks", {}).get("Stop", []) for h in g.get("hooks", [])]
    assert any(h["command"] == "user-script" for h in flat)
    assert not any("aiproof hook" in h["command"] for h in flat)


def test_claude_parse_event() -> None:
    event = ClaudeCodeAdapter().parse_event(
        {
            "hook_event_name": "Stop",
            "session_id": "s1",
            "cwd": "/tmp",
            "last_assistant_message": "all tests pass",
            "stop_hook_active": True,
        }
    )
    assert event.name == "Stop"
    assert event.session_id == "s1"
    assert event.last_message == "all tests pass"
    assert event.stop_hook_active is True


def test_mcp_adapter_writes_entry(tmp_path: Path) -> None:
    McpAdapter().install(tmp_path)
    data = json.loads((tmp_path / ".mcp.json").read_text())
    assert "aiproof" in data["mcpServers"]
    assert data["mcpServers"]["aiproof"]["command"] == "aiproof"


def test_mcp_snippet_shape() -> None:
    snippet = mcp_snippet()
    assert "mcpServers" in snippet


def test_detect_all_returns_adapters(tmp_path: Path) -> None:
    adapters = detect_all(tmp_path)
    assert all(hasattr(a, "id") for a in adapters)


def test_adapter_lookup() -> None:
    assert adapter("claude-code") is not None
    assert adapter("does-not-exist") is None
