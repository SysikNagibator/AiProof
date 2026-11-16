"""Sessions list screen."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table

from aiproof.config import Settings
from aiproof.i18n import t
from aiproof.ledger.store import LedgerStore
from aiproof.tui.theme import Theme


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Table:
    """Render the list of recorded sessions."""
    table = Table(title=t("menu.sessions", lang), border_style=theme.primary)
    table.add_column("#", justify="right")
    table.add_column("session")
    table.add_column("events", justify="right")
    counts: dict[str, int] = {}
    order: list[str] = []
    for record in LedgerStore(root).records():
        sid = record.get("session")
        if not isinstance(sid, str):
            continue
        if sid not in counts:
            order.append(sid)
            counts[sid] = 0
        counts[sid] += 1
    for index, sid in enumerate(order[-50:], start=1):
        table.add_row(str(index), sid, str(counts[sid]))
    if not order:
        table.add_row("-", "no sessions yet", "0")
    return table
