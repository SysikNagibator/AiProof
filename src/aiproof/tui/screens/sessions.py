"""Sessions list screen."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table

from aiproof.config import Settings
from aiproof.i18n import t
from aiproof.ledger.store import LedgerStore
from aiproof.tui.theme import Theme
from aiproof.tui.widgets import data_table


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Table:
    """Render the list of recorded sessions."""
    table = data_table(t("menu.sessions", lang), theme=theme, ascii_only=ascii_only)
    table.add_column("#", justify="right")
    table.add_column(t("tui.session", lang))
    table.add_column(t("tui.events", lang), justify="right")
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
    for index, sid in enumerate(order[-50:], start=max(1, len(order) - 49)):
        table.add_row(str(index), sid, str(counts[sid]))
    if not order:
        table.add_row("-", t("tui.no_sessions", lang), "0")
    return table
