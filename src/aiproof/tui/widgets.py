"""Reusable TUI widgets: header card, menu list, footer, help overlay."""

from __future__ import annotations

from collections.abc import Sequence

from rich.box import ROUNDED
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from aiproof.i18n import t
from aiproof.tui.logo import logo
from aiproof.tui.theme import Theme

MENU: tuple[tuple[str, str, str], ...] = (
    ("dashboard", "menu.dashboard", "status, agent, ledger"),
    ("live_feed", "menu.live_feed", "real-time events"),
    ("sessions", "menu.sessions", "past sessions"),
    ("checks", "menu.checks", "strictness and toggles"),
    ("secrets", "menu.secrets", "scan and redact"),
    ("rules", "menu.rules", "corrections"),
    ("settings", "menu.settings", "language, theme, agents"),
    ("doctor", "menu.doctor", "install integrity"),
    ("logs", "menu.logs", "aiproof.log"),
    ("update", "menu.update", "GitHub releases"),
    ("about", "menu.about", "version and license"),
    ("exit", "menu.exit", "leave AiProof"),
)


def header(
    theme: Theme,
    *,
    mode: str,
    agent: str,
    project: str,
    lang: str,
    last_verdict: str,
    ascii_only: bool = False,
) -> Panel:
    """Render the rounded header card with logo and status line."""
    title = logo(theme, ascii_only=ascii_only)
    dot = Text("● ", style=theme.ok)
    status = Text()
    status.append_text(dot)
    status.append(f"armed  {t('status.mode', lang, mode=mode)}  ")
    status.append(f"{t('status.agent', lang, agent=agent)}  ")
    status.append(f"{t('status.project', lang, project=project)}  ")
    status.append(f"{t('status.last_session', lang, verdict=last_verdict)}")
    body = Text()
    body.append_text(title)
    body.append("\n")
    body.append_text(status)
    return Panel(body, box=ROUNDED, border_style=theme.primary, expand=True)


def menu(theme: Theme, *, selected: int, lang: str, narrow: bool = False) -> Table:
    """Render the frameless numbered menu with the ``❯`` marker."""
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right", style=theme.dim)
    table.add_column()
    if not narrow:
        table.add_column(style=theme.dim)
    for index, (screen, key, desc) in enumerate(MENU):
        marker = "❯" if index == selected else " "
        danger = screen in ("exit",)
        style = theme.danger if (danger and index == selected) else ""
        label = f"{marker} {index + 1:>2}. {t(key, lang)}"
        if narrow:
            table.add_row("", Text(label, style=style))
        else:
            table.add_row("", Text(label, style=style), Text(desc, style=theme.dim))
    return table


def footer(theme: Theme, lang: str) -> Text:
    """Render the single dim footer line."""
    return Text(t("exit.keys", lang), style=theme.dim)


def help_overlay(theme: Theme, lang: str) -> Panel:
    """Render the help overlay."""
    text = Text()
    text.append("W/S, ↑/↓ ", style=theme.accent)
    text.append("move\n")
    text.append("Enter ", style=theme.accent)
    text.append("open\n")
    text.append("Esc/Backspace ", style=theme.accent)
    text.append("back\n")
    text.append("1-9 ", style=theme.accent)
    text.append("quick select\n")
    text.append("L/T ", style=theme.accent)
    text.append("language / theme\n")
    text.append("Q ", style=theme.accent)
    text.append("quit\n")
    return Panel(text, title=t("menu.about", lang), box=ROUNDED, border_style=theme.primary)


def stack(parts: Sequence[Text | Panel | Table]) -> Table:
    """Stack renderables vertically in one grid."""
    grid = Table.grid()
    for part in parts:
        grid.add_row(part)
    return grid
