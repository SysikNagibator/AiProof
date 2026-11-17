"""Doctor: integrity, install and environment diagnostics."""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from pathlib import Path

from aiproof import gitutil, paths
from aiproof.adapters.claude_code import ClaudeCodeAdapter
from aiproof.config import pinned_ok
from aiproof.i18n import t
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


def run(root: Path, lang: str = "en") -> list[Line]:
    """Run every doctor probe and return ordered findings (localized)."""
    lines: list[Line] = []

    lines.append(
        Line(
            OK,
            t("doc.python", lang, version=platform.python_version(), platform=sys.platform),
        )
    )
    lines.append(Line(OK, t("doc.data_dir", lang, path=paths.data_dir())))

    if gitutil.is_repo(root):
        lines.append(Line(OK, t("doc.git_repo", lang, path=root)))
    else:
        lines.append(Line(WARN, t("doc.not_git", lang), t("doc.not_git_hint", lang)))

    ok, reason = pinned_ok(root)
    lines.append(
        Line(
            OK if ok else FAIL,
            t("doc.pinned", lang, reason=reason),
            "" if ok else t("doc.pinned_hint", lang),
        )
    )

    result = verify.verify(root)
    lines.append(
        Line(
            OK if result.ok else FAIL,
            t("doc.ledger", lang, summary=result.summary()),
            "" if result.ok else t("doc.ledger_hint", lang),
        )
    )

    state, path = ClaudeCodeAdapter().hook_status(root)
    if state == "installed":
        lines.append(Line(OK, t("doc.hooks", lang, state=t("doc.installed", lang))))
    elif state == "malformed":
        lines.append(
            Line(
                WARN,
                t("doc.settings_malformed", lang, path=path or ""),
                t("doc.settings_malformed_hint", lang),
            )
        )
    elif state == "not_installed":
        lines.append(
            Line(
                WARN,
                t("doc.hooks", lang, state=t("doc.not_installed", lang)),
                t("doc.hooks_hint", lang),
            )
        )
    else:
        lines.append(Line(WARN, t("doc.settings_missing", lang), t("doc.hooks_hint", lang)))

    try:
        import rich  # noqa: F401

        lines.append(Line(OK, t("doc.rich_ok", lang)))
    except ModuleNotFoundError:
        lines.append(Line(WARN, t("doc.rich_missing", lang), t("doc.rich_hint", lang)))

    if ClaudeCodeAdapter().detect(root):
        lines.append(Line(OK, t("doc.detected", lang)))
    return lines


def as_dict(lines: list[Line]) -> list[dict[str, str]]:
    """Return doctor lines as JSON-safe mappings."""
    return [{"level": ln.level, "label": ln.label, "hint": ln.hint} for ln in lines]


def has_failures(lines: list[Line]) -> bool:
    """Return True when any probe failed."""
    return any(ln.level == FAIL for ln in lines)
