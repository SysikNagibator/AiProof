"""Doctor: integrity, install and environment diagnostics."""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from pathlib import Path

from aiproof import gitutil, paths
from aiproof.adapters.claude_code import ClaudeCodeAdapter
from aiproof.config import pinned_ok
from aiproof.ledger import verify

OK = "ok"
WARN = "warn"
FAIL = "fail"


@dataclass(slots=True)
class Line:
    """One doctor line."""

    level: str
    label: str
    hint: str = ""


def run(root: Path) -> list[Line]:
    """Run every doctor probe and return ordered findings."""
    lines: list[Line] = []

    lines.append(Line(OK, f"Python {platform.python_version()} ({sys.platform})"))
    lines.append(Line(OK, f"data dir: {paths.data_dir()}"))

    if gitutil.is_repo(root):
        lines.append(Line(OK, f"git repo: {root}"))
    else:
        lines.append(Line(WARN, "not a git repository", "run `git init` for full verification"))

    ok, reason = pinned_ok(root)
    lines.append(
        Line(
            OK if ok else FAIL,
            f"pinned config: {reason}",
            "" if ok else "run `aiproof init` in an interactive terminal",
        )
    )

    result = verify.verify(root)
    lines.append(
        Line(
            OK if result.ok else FAIL,
            f"ledger: {result.summary()}",
            "" if result.ok else "inspect ~/.aiproof/projects/*/ledger*.jsonl",
        )
    )

    settings_file = root / ".claude" / "settings.json"
    if settings_file.is_file():
        text = settings_file.read_text(encoding="utf-8")
        installed = "aiproof hook" in text
        lines.append(
            Line(
                OK if installed else WARN,
                "claude-code hooks: " + ("installed" if installed else "not installed"),
                "" if installed else "run `aiproof init`",
            )
        )
    else:
        lines.append(Line(WARN, "claude-code settings: not found", "run `aiproof init`"))

    try:
        import rich  # noqa: F401

        lines.append(Line(OK, "rich available (TUI enabled)"))
    except ModuleNotFoundError:
        lines.append(Line(WARN, "rich missing", "pip install rich"))

    if ClaudeCodeAdapter().detect(root):
        lines.append(Line(OK, "claude-code detected"))
    return lines


def as_dict(lines: list[Line]) -> list[dict[str, str]]:
    """Return doctor lines as JSON-safe mappings."""
    return [{"level": ln.level, "label": ln.label, "hint": ln.hint} for ln in lines]


def has_failures(lines: list[Line]) -> bool:
    """Return True when any probe failed."""
    return any(ln.level == FAIL for ln in lines)
