"""Install / uninstall hooks and write pins."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from aiproof import logging, paths
from aiproof.adapters import detect_all
from aiproof.adapters.base import Adapter
from aiproof.adapters.claude_code import ClaudeCodeAdapter
from aiproof.config import Settings, load_settings, write_pinned
from aiproof.guard.pin import verify_pins

ALLOW_TEMPLATE = """# AiProof secrets allowlist (pinned by `aiproof init`).
paths = []
regexes = []
fingerprints = []
"""


@dataclass(slots=True)
class InitReport:
    """What ``aiproof init`` did."""

    project: str
    detected: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    pinned_sha256: str = ""
    dry_run: bool = False


def init_project(root: Path, *, dry_run: bool = False, level: str = "project") -> InitReport:
    """Initialize AiProof for a project: install hooks and write pins."""
    report = InitReport(project=str(paths.canonical_path(root)), dry_run=dry_run)
    settings: Settings = load_settings(root)

    detected: list[Adapter] = detect_all(root)
    report.detected = [a.id for a in detected]

    # Claude Code hooks are the only blocking (native-hook) integration and the
    # default target, so ``init`` always installs them. Without this, a repo that
    # only has e.g. ``.mcp.json`` would report success while leaving the gate
    # silently inactive (detect_all would return just the MCP adapter).
    targets: list[Adapter] = list(detected)
    if not any(a.id == "claude-code" for a in targets):
        targets.append(ClaudeCodeAdapter())
        report.detected.append("claude-code (assumed)")

    for adapter in targets:
        if adapter.id != "claude-code":
            continue
        result = adapter.install(root, dry_run=dry_run, level=level)  # type: ignore[call-arg]
        report.changed.extend(result.changed)
        report.backups.extend(result.backups)
        report.skipped.extend(result.skipped)

    allow = paths.project_allow_path(root)
    if not allow.is_file() and not dry_run:
        allow.parent.mkdir(parents=True, exist_ok=True)
        allow.write_text(ALLOW_TEMPLATE, encoding="utf-8")
        report.changed.append(str(allow))

    if not dry_run:
        paths.project_dir(root).mkdir(parents=True, exist_ok=True)
        report.pinned_sha256 = write_pinned(root, settings).sha256
        logging.log(f"init project={root} pinned={report.pinned_sha256[:12]}")
    return report


def uninstall_project(root: Path, *, dry_run: bool = False) -> list[str]:
    """Remove AiProof's own hook entries (never user entries)."""
    changed: list[str] = []
    targets: list[Adapter] = list(detect_all(root))
    # Always attempt to strip our Claude Code hooks, even when only a different
    # adapter is currently detected (e.g. a leftover user-level install).
    if not any(a.id == "claude-code" for a in targets):
        targets.append(ClaudeCodeAdapter())
    for adapter in targets:
        result = adapter.uninstall(root, dry_run=dry_run)
        changed.extend(result.changed)
        changed.extend(result.skipped)
    return changed


def status(root: Path) -> dict[str, object]:
    """Return a status summary for the doctor/status command."""
    ok, reason = verify_pins(root)
    return {
        "project": str(paths.canonical_path(root)),
        "data_dir": str(paths.data_dir()),
        "pinned_ok": ok,
        "pinned_reason": reason,
        "agents": [a.id for a in detect_all(root)],
    }
