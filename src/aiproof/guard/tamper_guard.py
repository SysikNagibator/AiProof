"""Tamper guard: PreToolUse deny rules and shell-command heuristics."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from aiproof.checks.config_integrity import protected_path
from aiproof.config import Settings

# Bare protected names always defended, in addition to pinned settings.
ALWAYS_PROTECTED: tuple[str, ...] = (
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".claude/hooks/**",
    ".mcp.json",
    ".cursor/mcp.json",
    "**/mcp.json",
    ".aiproof/**",
    "**/pinned.toml",
    "**/ledger*.jsonl",
)

# Shell verbs that write/move/delete, and redirection operators.
_WRITE_VERBS = re.compile(
    r"\b(rm|mv|cp|tee|sed|truncate|dd|install|chmod|chown|Set-Content|Remove-Item|"
    r"Set-Item|Clear-Content|Out-File|copy|del|move|ren)\b",
    re.IGNORECASE,
)
_REDIRECT = re.compile(r"(?:>>?|>\s*\|)")


def _patterns(settings: Settings) -> tuple[str, ...]:
    return tuple(settings.protected_paths) + ALWAYS_PROTECTED


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return re.split(r"\s+", command)


def shell_hits_protected(command: str, settings: Settings) -> str | None:
    """Return the protected token a shell command targets, or ``None``."""
    if not command:
        return None
    tokens = _tokens(command)
    patterns = _patterns(settings)
    for token in tokens:
        cleaned = token.strip("\"'").replace("\\", "/")
        if token in (">", ">>"):
            continue
        if protected_path(Path(cleaned), patterns):
            return cleaned
    # Substring fallback for quoted/obfuscated forms.
    lowered = command.replace("\\", "/").lower()
    for pat in patterns:
        needle = pat.replace("{data}", "").replace("**", "").strip("/").lower()
        if needle and needle in lowered and _WRITE_VERBS.search(command):
            return needle
    if _REDIRECT.search(command):
        for pat in patterns:
            needle = pat.replace("{data}", "").replace("**", "").strip("/").lower()
            if needle and needle in lowered:
                return needle
    return None


def guard_tool(tool_name: str, tool_input: dict[str, object], settings: Settings) -> str | None:
    """Return a denial reason for a tool call that touches protected paths."""
    if settings.strictness == "observe":
        return None
    patterns = _patterns(settings)

    if tool_name in ("Bash", "PowerShell", "Monitor"):
        command = str(tool_input.get("command", ""))
        hit = shell_hits_protected(command, settings)
        if hit:
            return f"AiProof: writing to protected path '{hit}' is not allowed."
        return None

    if tool_name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = str(
            tool_input.get("file_path")
            or tool_input.get("notebook_path")
            or tool_input.get("path")
            or ""
        )
        if path and protected_path(Path(path.replace("\\", "/")), patterns):
            return f"AiProof: editing protected file '{path}' is not allowed."
    return None
