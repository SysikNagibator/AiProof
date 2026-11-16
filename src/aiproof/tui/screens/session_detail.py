"""Session detail ("the receipt") screen."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text

from aiproof.config import Settings
from aiproof.ledger.receipt import build_receipt, render_md
from aiproof.ledger.store import LedgerStore
from aiproof.tui.theme import Theme


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Text:
    """Render the latest session receipt as Markdown-ish text."""
    session = LedgerStore(root).last_session()
    if session is None:
        return Text("no sessions recorded yet", style=theme.dim)
    return Text(render_md(build_receipt(root, session)))
