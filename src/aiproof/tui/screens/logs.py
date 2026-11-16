"""Logs screen: tail of AiProof's own log."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text

from aiproof import paths
from aiproof.config import Settings
from aiproof.tui.theme import Theme


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Text:
    """Render the last lines of the AiProof log."""
    target = paths.log_path()
    if not target.is_file():
        return Text("no logs yet", style=theme.dim)
    lines = target.read_text(encoding="utf-8").splitlines()[-40:]
    return Text("\n".join(lines) or "no logs yet")
