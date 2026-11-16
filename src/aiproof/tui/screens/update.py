"""Update screen."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text

from aiproof.config import Settings
from aiproof.tui.theme import Theme


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Text:
    """Render the update hint (network is never used from the TUI render path)."""
    hint = (
        "Updates require explicit consent and a checksum-verified manifest.\n"
        "Run: aiproof update --check"
    )
    return Text(hint, style=theme.dim)
