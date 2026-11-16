"""Doctor screen."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table
from rich.text import Text

from aiproof.config import Settings
from aiproof.i18n import t
from aiproof.maintenance import doctor
from aiproof.tui.theme import Theme


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Table:
    """Render the doctor probes."""
    table = Table(title=t("menu.doctor", lang), border_style=theme.primary)
    table.add_column("")
    table.add_column("check")
    table.add_column("hint")
    marks = {"ok": ("✓", theme.ok), "warn": ("!", theme.warn), "fail": ("✗", theme.danger)}
    for line in doctor.run(root):
        mark, style = marks.get(line.level, ("?", theme.dim))
        table.add_row(Text(mark, style=style), line.label, line.hint)
    return table
