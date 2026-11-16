"""Claude Code adapter (native hooks).

Verified against the current Claude Code hooks reference and guide (2026-11-16):
events, stdin JSON, exit codes, JSON decisions, ``stop_hook_active``, and the
``.claude/settings*.json`` locations.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from aiproof.adapters.base import Adapter, Event, InstallResult, SupportLevel

MARKER = "aiproof hook"

# event -> matcher (None = no matcher / fires on every occurrence)
HOOK_EVENTS: dict[str, str | None] = {
    "SessionStart": None,
    "PreToolUse": "Bash|Edit|Write|MultiEdit|NotebookEdit",
    "PostToolUse": "Bash|Edit|Write|MultiEdit|NotebookEdit",
    "Stop": None,
}


def _settings_path(root: Path, level: str) -> Path:
    if level == "user":
        return Path.home() / ".claude" / "settings.json"
    if level == "local":
        return root / ".claude" / "settings.local.json"
    return root / ".claude" / "settings.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _hook_command(event: str) -> str:
    return f"{MARKER} {event}"


def _is_ours(hook: dict[str, Any]) -> bool:
    command = hook.get("command")
    return isinstance(command, str) and MARKER in command


def _our_hook_entry(event: str) -> dict[str, Any]:
    return {"type": "command", "command": _hook_command(event), "timeout": 30}


class ClaudeCodeAdapter(Adapter):
    """Install/remove AiProof hooks in Claude Code settings files."""

    id = "claude-code"
    support = SupportLevel.NATIVE_HOOKS

    def detect(self, root: Path) -> bool:
        """Detect Claude Code by project markers or a user settings file."""
        return (
            (root / ".claude").is_dir()
            or (root / "CLAUDE.md").is_file()
            or (Path.home() / ".claude" / "settings.json").is_file()
        )

    def _merge(self, settings: dict[str, Any]) -> dict[str, Any]:
        hooks = settings.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            hooks = {}
            settings["hooks"] = hooks
        for event, matcher in HOOK_EVENTS.items():
            groups = hooks.setdefault(event, [])
            if not isinstance(groups, list):
                groups = []
                hooks[event] = groups
            # Drop our previous entry for this event, then re-add (idempotent).
            cleaned: list[Any] = []
            for group in groups:
                if isinstance(group, dict):
                    inner_hooks = group.get("hooks", [])
                    inner = [h for h in inner_hooks if not _is_ours(h)]
                    if inner:
                        group["hooks"] = inner
                        cleaned.append(group)
                    # A group with only our hooks (or none) is dropped.
                else:
                    cleaned.append(group)
            entry: dict[str, Any] = {"hooks": [_our_hook_entry(event)]}
            if matcher is not None:
                entry["matcher"] = matcher
            cleaned.append(entry)
            hooks[event] = cleaned
        return settings

    def _strip(self, settings: dict[str, Any]) -> dict[str, Any]:
        hooks = settings.get("hooks")
        if not isinstance(hooks, dict):
            return settings
        for event in list(hooks):
            groups = hooks.get(event)
            if not isinstance(groups, list):
                continue
            remaining: list[Any] = []
            for group in groups:
                if not isinstance(group, dict):
                    remaining.append(group)
                    continue
                inner = [h for h in group.get("hooks", []) if not _is_ours(h)]
                if inner:
                    group["hooks"] = inner
                    remaining.append(group)
            if remaining:
                hooks[event] = remaining
            else:
                hooks.pop(event, None)
        if not hooks:
            settings.pop("hooks", None)
        return settings

    def install(
        self, root: Path, *, dry_run: bool = False, level: str = "project"
    ) -> InstallResult:
        """Install hooks (project level by default)."""
        path = _settings_path(root, level)
        result = InstallResult()
        original = _read_json(path)
        merged = self._merge(json.loads(json.dumps(original)))
        if dry_run:
            result.skipped.append(os.fspath(path))
            return result
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            backup = path.with_suffix(path.suffix + ".bak")
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            result.backups.append(os.fspath(backup))
        path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        result.changed.append(os.fspath(path))
        return result

    def uninstall(self, root: Path, *, dry_run: bool = False) -> InstallResult:
        """Remove AiProof's own hook entries."""
        result = InstallResult()
        for level in ("project", "local"):
            path = _settings_path(root, level)
            if not path.is_file():
                continue
            stripped = self._strip(_read_json(path))
            if dry_run:
                result.skipped.append(os.fspath(path))
                continue
            path.write_text(json.dumps(stripped, indent=2) + "\n", encoding="utf-8")
            result.changed.append(os.fspath(path))
        return result

    def parse_event(self, raw: dict[str, Any]) -> Event:
        """Normalize a Claude Code hook payload."""
        cwd = raw.get("cwd")
        return Event(
            name=str(raw.get("hook_event_name", "")),
            session_id=str(raw.get("session_id", "unknown")),
            cwd=Path(str(cwd)) if cwd else Path.cwd(),
            tool_name=str(raw.get("tool_name", "")),
            tool_input=raw.get("tool_input", {}) if isinstance(raw.get("tool_input"), dict) else {},
            prompt=str(raw.get("prompt", "")),
            last_message=str(raw.get("last_assistant_message", "") or raw.get("message", "")),
            stop_hook_active=bool(raw.get("stop_hook_active", False)),
            raw=raw,
        )

    def stop_response(self, block: bool, reason: str) -> tuple[int, dict[str, Any]]:
        """Return the Stop-hook JSON decision."""
        if block and reason:
            return 0, {"decision": "block", "reason": reason}
        return 0, {}

    def pretooluse_deny(self, reason: str) -> tuple[int, dict[str, Any]]:
        """Return a PreToolUse deny decision."""
        return 0, {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
