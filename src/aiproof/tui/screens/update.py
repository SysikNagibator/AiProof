"""Update screen."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text

from aiproof.config import Settings
from aiproof.i18n import t
from aiproof.tui.theme import Theme


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Text:
    """Render the update hint (network is never used from the TUI render path)."""
    return Text(t("update.body", lang), style=theme.dim)
