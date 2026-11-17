"""Claude Code adapter (native hooks).

Verified against the current Claude Code hooks reference and guide (2026-11-16):
events, stdin JSON, exit codes, JSON decisions, ``stop_hook_active``, and the
``.claude/settings*.json`` locations.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from aiproof.adapters.base import Adapter, Event, InstallResult, SupportLevel

MARKER = "aiproof hook"


class MalformedSettingsError(ValueError):
    """Raised when an agent settings file exists but is not a JSON object."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"malformed JSON settings file: {path}")
        self.path = path


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
    """Read a settings file.

    A missing file yields ``{}``. A file that exists but is not a JSON object raises
    :class:`MalformedSettingsError` — callers must leave it untouched instead of
    overwriting the user's settings with a partial object.
    """
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise MalformedSettingsError(path) from exc
    if not isinstance(data, dict):
        raise MalformedSettingsError(path)
    return data


def _hook_command(event: str) -> str:
    return f"{MARKER} {event}"


def _is_ours(hook: Any) -> bool:
    if not isinstance(hook, dict):
        return False
    command = hook.get("command")
    return isinstance(command, str) and MARKER in command


def _has_our_hooks(settings: dict[str, Any]) -> bool:
    """Return True when *settings* contains at least one AiProof hook entry."""
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    for groups in hooks.values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if isinstance(group, dict) and any(_is_ours(hook) for hook in group.get("hooks", [])):
                return True
    return False


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

    def hook_status(self, root: Path) -> tuple[str, Path | None]:
        """Report our hooks across project/local/user settings.

        Returns ``(state, path)`` where state is ``installed``, ``not_installed``,
        ``malformed`` or ``missing``. Parsing is JSON-based, so a malformed file
        that merely contains the marker string is not reported as installed.
        """
        malformed: Path | None = None
        seen = False
        for level in ("project", "local", "user"):
            path = _settings_path(root, level)
            if not path.is_file():
                continue
            seen = True
            try:
                settings = _read_json(path)
            except MalformedSettingsError:
                malformed = malformed or path
                continue
            if _has_our_hooks(settings):
                return "installed", path
        if malformed is not None:
            return "malformed", malformed
        return ("not_installed" if seen else "missing"), None

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
        try:
            original = _read_json(path)
        except MalformedSettingsError:
            # Never replace a file we could not parse.
            result.skipped.append(os.fspath(path))
            return result
        merged = self._merge(copy.deepcopy(original))
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
        """Remove AiProof's own hook entries from project, local and user settings."""
        result = InstallResult()
        for level in ("project", "local", "user"):
            path = _settings_path(root, level)
            if not path.is_file():
                continue
            try:
                original = _read_json(path)
            except MalformedSettingsError:
                result.skipped.append(os.fspath(path))
                continue
            if not _has_our_hooks(original):
                continue
            stripped = self._strip(copy.deepcopy(original))
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
