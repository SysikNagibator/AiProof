"""Live feed screen: the most recent ledger events with verdict colors."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.table import Table

from aiproof.config import Settings
from aiproof.i18n import t
from aiproof.ledger.store import LedgerStore
from aiproof.tui.theme import Theme

LIMIT = 30


def _detail(record: dict[str, Any]) -> str:
    payload = record.get("payload", {})
    if not isinstance(payload, dict):
        return ""
    event = record.get("event")
    if event == "gate_decision":
        return "BLOCK" if payload.get("block") else "ok"
    if event == "claims_extracted":
        return f"claims={payload.get('count')}"
    if event in ("tool_pre", "tool_post"):
        return str(payload.get("command", ""))[:60]
    if event == "tamper_attempt":
        return str(payload.get("reason", ""))[:60]
    if event == "correction":
        return str(payload.get("text", ""))[:60]
    return ""


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Table:
    """Render recent events (refresh with R)."""
    table = Table(title=t("menu.live_feed", lang), border_style=theme.primary)
    table.add_column("time", style=theme.dim)
    table.add_column("event")
    table.add_column("session", style=theme.dim)
    table.add_column("detail")
    records = LedgerStore(root).records()[-LIMIT:]
    if not records:
        table.add_row("-", "no events yet", "-", "-")
        return table
    for record in records:
        event = str(record.get("event", "?"))
        payload = record.get("payload", {})
        blocked = (
            event == "gate_decision" and isinstance(payload, dict) and bool(payload.get("block"))
        )
        style = theme.danger if event == "tamper_attempt" or blocked else ""
        table.add_row(
            str(record.get("ts", ""))[11:19],
            event,
            str(record.get("session", ""))[:12],
            _detail(record),
            style=style,
        )
    return table
