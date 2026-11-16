"""Secrets screen: scan the diff (types only)."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table

from aiproof import paths
from aiproof.config import Settings
from aiproof.i18n import t
from aiproof.redact.redactor import load_allowlist
from aiproof.redact.scanner import scan_diff
from aiproof.tui.theme import Theme


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Table:
    """Render secret findings from the current diff."""
    table = Table(title=t("menu.secrets", lang), border_style=theme.primary)
    table.add_column("type")
    table.add_column("location")
    table.add_column("fingerprint")
    allow = load_allowlist(paths.project_allow_path(root))
    allow.compile()
    findings = scan_diff(root, allow)
    if not findings:
        table.add_row("-", "no secrets found", "-")
    for finding in findings:
        table.add_row(finding.type, f"{finding.path}:{finding.line}", finding.fingerprint)
    return table
