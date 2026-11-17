"""Reusable TUI widgets: header card, menu list, footer, help overlay."""

from __future__ import annotations

from collections.abc import Sequence

from rich import box as rich_box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from aiproof.i18n import t
from aiproof.tui.logo import logo
from aiproof.tui.theme import Theme, ascii_safe

MENU: tuple[tuple[str, str, str], ...] = (
    ("dashboard", "menu.dashboard", "menu_desc.dashboard"),
    ("live_feed", "menu.live_feed", "menu_desc.live_feed"),
    ("sessions", "menu.sessions", "menu_desc.sessions"),
    ("checks", "menu.checks", "menu_desc.checks"),
    ("secrets", "menu.secrets", "menu_desc.secrets"),
    ("rules", "menu.rules", "menu_desc.rules"),
    ("settings", "menu.settings", "menu_desc.settings"),
    ("doctor", "menu.doctor", "menu_desc.doctor"),
    ("logs", "menu.logs", "menu_desc.logs"),
    ("update", "menu.update", "menu_desc.update"),
    ("about", "menu.about", "menu_desc.about"),
    ("exit", "menu.exit", "menu_desc.exit"),
)


def _panel_box(ascii_only: bool) -> rich_box.Box:
    return rich_box.ASCII if ascii_only else rich_box.ROUNDED


def data_table(title: str, *, theme: Theme, ascii_only: bool) -> Table:
    """Build a bordered data table that switches to ASCII box drawing on demand."""
    return Table(
        title=title,
        border_style=theme.primary,
        box=rich_box.ASCII if ascii_only else rich_box.HEAVY_HEAD,
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
    dot = Text("* " if ascii_only else "● ", style=theme.ok)
    status = Text()
    status.append_text(dot)
    status.append(f"{t('status.armed', lang)}  {t('status.mode', lang, mode=mode)}  ")
    status.append(f"{t('status.agent', lang, agent=agent)}  ")
    status.append(f"{t('status.project', lang, project=project)}  ")
    status.append(f"{t('status.last_session', lang, verdict=last_verdict)}")
    body = Text()
    body.append_text(title)
    body.append("\n")
    body.append_text(status)
    return Panel(body, box=_panel_box(ascii_only), border_style=theme.primary, expand=True)


def menu(
    theme: Theme, *, selected: int, lang: str, narrow: bool = False, ascii_only: bool = False
) -> Table:
    """Render the frameless numbered menu with the selection marker."""
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right", style=theme.dim)
    table.add_column()
    if not narrow:
        table.add_column(style=theme.dim)
    for index, (screen, key, desc) in enumerate(MENU):
        marker = (">" if ascii_only else "❯") if index == selected else " "
        danger = screen in ("exit",)
        style = theme.danger if (danger and index == selected) else ""
        label = t(key, lang)
        description = t(desc, lang)
        if ascii_only:
            label = ascii_safe(label)
            description = ascii_safe(description)
        label = f"{marker} {index + 1:>2}. {label}"
        if narrow:
            table.add_row("", Text(label, style=style))
        else:
            table.add_row("", Text(label, style=style), Text(description, style=theme.dim))
    return table


def footer(theme: Theme, lang: str, ascii_only: bool = False) -> Text:
    """Render the single dim footer line."""
    keys = t("exit.keys", lang)
    return Text(ascii_safe(keys) if ascii_only else keys, style=theme.dim)


def help_overlay(theme: Theme, lang: str, ascii_only: bool = False) -> Panel:
    """Render the help overlay."""
    arrows = "^/v " if ascii_only else "↑/↓ "
    text = Text()
    text.append("W/S, " + arrows, style=theme.accent)
    text.append(t("helpo.move", lang) + "\n")
    text.append("Enter ", style=theme.accent)
    text.append(t("helpo.open", lang) + "\n")
    text.append("Esc/Backspace ", style=theme.accent)
    text.append(t("helpo.back", lang) + "\n")
    text.append("1-9 ", style=theme.accent)
    text.append(t("helpo.quick_select", lang) + "\n")
    text.append("L/T ", style=theme.accent)
    text.append(t("helpo.lang_theme", lang) + "\n")
    text.append("Q ", style=theme.accent)
    text.append(t("helpo.quit", lang) + "\n")
    return Panel(
        text,
        title=t("helpo.title", lang),
        box=_panel_box(ascii_only),
        border_style=theme.primary,
    )


def stack(parts: Sequence[Text | Panel | Table]) -> Table:
    """Stack renderables vertically in one grid."""
    grid = Table.grid()
    for part in parts:
        grid.add_row(part)
    return grid
