"""Tamper guard: PreToolUse denials and human-only actions."""

from __future__ import annotations

import pytest

from aiproof.config import Settings
from aiproof.guard import tamper_guard
from aiproof.guard.pin import HumanOnlyError, require_human


def test_shell_hits_protected_rm() -> None:
    settings = Settings()
    assert tamper_guard.shell_hits_protected("rm .claude/settings.json", settings)


def test_shell_hits_protected_redirect() -> None:
    settings = Settings()
    assert tamper_guard.shell_hits_protected("echo '{}' > .claude/settings.json", settings)


def test_shell_ignores_innocent_command() -> None:
    settings = Settings()
    assert tamper_guard.shell_hits_protected("pytest -q", settings) is None


def test_guard_tool_write_denied() -> None:
    settings = Settings()
    reason = tamper_guard.guard_tool("Write", {"file_path": ".claude/settings.json"}, settings)
    assert reason and "protected" in reason


def test_guard_tool_bash_denied() -> None:
    settings = Settings()
    reason = tamper_guard.guard_tool("Bash", {"command": "sed -i s/x/y/ .mcp.json"}, settings)
    assert reason


def test_guard_tool_allows_normal_edit() -> None:
    settings = Settings()
    assert tamper_guard.guard_tool("Write", {"file_path": "src/app.py"}, settings) is None


def test_guard_observe_never_denies() -> None:
    settings = Settings(strictness="observe")
    assert (
        tamper_guard.guard_tool("Write", {"file_path": ".claude/settings.json"}, settings) is None
    )


def test_require_human_raises_when_non_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIPROOF_NON_INTERACTIVE", "1")
    with pytest.raises(HumanOnlyError):
        require_human("pause")


def test_require_human_raises_in_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIPROOF_NON_INTERACTIVE", raising=False)
    monkeypatch.setenv("CI", "true")
    with pytest.raises(HumanOnlyError):
        require_human("pin")
