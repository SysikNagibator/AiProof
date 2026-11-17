"""Doctor screen."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table
from rich.text import Text

from aiproof.config import Settings
from aiproof.i18n import t
from aiproof.maintenance import doctor
from aiproof.tui.theme import Theme
from aiproof.tui.widgets import data_table


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Table:
    """Render the doctor probes."""
    table = data_table(t("menu.doctor", lang), theme=theme, ascii_only=ascii_only)
    table.add_column("")
    table.add_column(t("tui.check", lang))
    table.add_column(t("tui.hint", lang))
    marks = {
        "ok": ("v" if ascii_only else "✓", theme.ok),
        "warn": ("!", theme.warn),
        "fail": ("x" if ascii_only else "✗", theme.danger),
    }
    for line in doctor.run(root, lang):
        mark, style = marks.get(line.level, ("?", theme.dim))
        table.add_row(Text(mark, style=style), line.label, line.hint)
    return table
