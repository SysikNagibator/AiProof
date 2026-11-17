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
    table.add_column(t("tui.key", lang))
    table.add_column(t("tui.value", lang))
    note = "" if is_reviewed(lang) else " " + t("tui.machine_translated", lang)
    table.add_row(t("tui.language", lang), f"{lang}{note}")
    table.add_row(t("tui.available", lang), ", ".join(available()))
    table.add_row(t("tui.theme", lang), theme.name)
    table.add_row(t("tui.strictness", lang), settings.strictness)
    table.add_row(t("tui.on_internal_error", lang), settings.on_internal_error)
    table.add_row(t("tui.test_command", lang), settings.test_command or t("tui.autodetect", lang))
    table.add_row(t("tui.agent_message_language", lang), settings.agent_message_language)
    table.add_row(t("tui.current_language", lang), detect_language())
    return table
