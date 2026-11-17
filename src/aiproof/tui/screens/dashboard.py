"""Dashboard screen: armed state, pins, ledger, agents, recent sessions."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table
from rich.text import Text

from aiproof.adapters import detect_all
from aiproof.config import Settings, pinned_ok
from aiproof.i18n import t
from aiproof.ledger import verify
from aiproof.ledger.store import LedgerStore
from aiproof.tui.theme import Theme


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Table:
    """Render the dashboard."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style=theme.dim)
    grid.add_column()

    ok, reason = pinned_ok(root)
    v = verify.verify(root)
    store = LedgerStore(root)
    sessions = []
    for record in store.records():
        sid = record.get("session")
        if isinstance(sid, str) and sid not in sessions:
            sessions.append(sid)

    grid.add_row(t("tui.armed", lang), Text(t("status.armed", lang), style=theme.ok))
    grid.add_row(t("tui.mode", lang), settings.strictness)
    grid.add_row(
        t("tui.pinned", lang),
        Text("✓ ok" if ok else f"✗ {reason}", style=theme.ok if ok else theme.danger),
    )
    grid.add_row(t("tui.ledger", lang), Text(v.summary(), style=theme.ok if v.ok else theme.danger))
    agents = ", ".join(a.id for a in detect_all(root)) or t("tui.none", lang)
    grid.add_row(t("tui.agents", lang), agents)
    grid.add_row(t("tui.sessions", lang), t("count.sessions", lang, n=len(sessions)))
    grid.add_row(t("tui.data_dir", lang), str(root.parent if root.parent != root else root))
    return grid
