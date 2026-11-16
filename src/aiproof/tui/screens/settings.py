"""Settings screen."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table

from aiproof.config import Settings
from aiproof.i18n import available, detect_language, is_reviewed, t
from aiproof.tui.theme import Theme


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Table:
    """Render the effective settings."""
    table = Table(title=t("menu.settings", lang), border_style=theme.primary)
    table.add_column("key")
    table.add_column("value")
    table.add_row("language", f"{lang}{'' if is_reviewed(lang) else ' (machine-translated)'}")
    table.add_row("available", ", ".join(available()))
    table.add_row("theme", theme.name)
    table.add_row("strictness", settings.strictness)
    table.add_row("on_internal_error", settings.on_internal_error)
    table.add_row("test_command", settings.test_command or "(autodetect)")
    table.add_row("agent_message_language", settings.agent_message_language)
    table.add_row("current language", detect_language())
    return table
