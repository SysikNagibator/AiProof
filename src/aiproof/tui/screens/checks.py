"""Checks screen: enabled checks and strictness."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table
from rich.text import Text

from aiproof.checks import ALL_CHECK_NAMES
from aiproof.config import Settings
from aiproof.i18n import t
from aiproof.tui.theme import Theme


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Table:
    """Render the check toggles and strictness."""
    table = Table(title=t("menu.checks", lang), border_style=theme.primary)
    table.add_column(t("tui.check", lang))
    table.add_column(t("tui.state", lang))
    table.add_row(t("tui.strictness", lang), Text(settings.strictness, style=theme.accent))
    for name in ALL_CHECK_NAMES:
        enabled = (
            f"✓ {t('tui.on', lang)}"
            if name in settings.enabled_checks
            else f"· {t('tui.off', lang)}"
        )
        style = theme.ok if name in settings.enabled_checks else theme.dim
        table.add_row(name, Text(enabled, style=style))
    return table
