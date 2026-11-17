"""Checks screen: enabled checks and strictness."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table
from rich.text import Text

from aiproof.checks import ALL_CHECK_NAMES
from aiproof.config import Settings
from aiproof.i18n import t
from aiproof.tui.theme import Theme
from aiproof.tui.widgets import data_table


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Table:
    """Render the check toggles and strictness."""
    table = data_table(t("menu.checks", lang), theme=theme, ascii_only=ascii_only)
    table.add_column(t("tui.check", lang))
    table.add_column(t("tui.state", lang))
    table.add_row(t("tui.strictness", lang), Text(settings.strictness, style=theme.accent))
    for name in ALL_CHECK_NAMES:
        on, off = ("v", "-") if ascii_only else ("✓", "·")
        enabled = (
            f"{on} {t('tui.on', lang)}"
            if name in settings.enabled_checks
            else f"{off} {t('tui.off', lang)}"
        )
        style = theme.ok if name in settings.enabled_checks else theme.dim
        table.add_row(name, Text(enabled, style=style))
    return table
