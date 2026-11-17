"""Dashboard screen: armed state, pins, ledger, agents, recent sessions."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table
from rich.text import Text

from aiproof.adapters import detect_all
from aiproof.config import Settings, pinned_ok
from aiproof.i18n import plural, t
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

    pinned_text = t("tui.pin_missing", lang) if "missing" in reason else t("tui.pin_tampered", lang)
    if v.ok:
        ledger_text = t("tui.chain_ok", lang, n=v.checked, segments=v.segments)
    else:
        seq = v.first_broken_seq if v.first_broken_seq is not None else "?"
        ledger_text = t("tui.chain_broken", lang, seq=seq)
    ok_mark, bad_mark = ("v ", "x ") if ascii_only else ("✓ ", "✗ ")

    grid.add_row(t("tui.armed", lang), Text(t("status.armed", lang), style=theme.ok))
    grid.add_row(t("tui.mode", lang), settings.strictness)
    grid.add_row(
        t("tui.pinned", lang),
        Text(
            (ok_mark + t("doctor.ok", lang)) if ok else f"{bad_mark}{pinned_text}",
            style=theme.ok if ok else theme.danger,
        ),
    )
    grid.add_row(t("tui.ledger", lang), Text(ledger_text, style=theme.ok if v.ok else theme.danger))
    agents = ", ".join(a.id for a in detect_all(root)) or t("tui.none", lang)
    grid.add_row(t("tui.agents", lang), agents)
    grid.add_row(t("tui.sessions", lang), plural("sessions", len(sessions), lang))
    grid.add_row(t("tui.data_dir", lang), str(root.parent if root.parent != root else root))
    return grid
