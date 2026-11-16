"""The AiProof TUI: one Live frame, alternate screen, event-driven redraw."""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from aiproof import paths
from aiproof.config import Settings, load_settings
from aiproof.i18n import KNOWN_LANGS, available, detect_language
from aiproof.ledger.store import LedgerStore
from aiproof.tui import keys, widgets
from aiproof.tui.screens import render as render_screen
from aiproof.tui.theme import resolve

THEME_CYCLE = ("green", "mono", "amber")


@dataclass
class State:
    """Mutable TUI state."""

    selected: int = 0
    screen: str | None = None
    lang: str = "en"
    theme_name: str = "green"
    help: bool = False
    ascii_only: bool = False
    narrow: bool = False
    dirty: bool = True


def _read_key() -> str:
    """Read a single key (layout-independent), POSIX + Windows."""
    if os.name == "nt":  # pragma: no cover - Windows console
        import msvcrt

        getwch = cast("Any", msvcrt).getwch
        char = getwch()
        if char in ("\x00", "\xe0"):
            second = getwch()
            return {"H": "up", "P": "down", "G": "home", "O": "end"}.get(second, "")
        return keys.key_name(char.encode("utf-8", "ignore"))

    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        chunk = os.read(fd, 1)
        if chunk == b"\x1b":
            os.set_blocking(fd, False)
            time.sleep(0.01)
            try:
                more = os.read(fd, 8)
            except BlockingIOError:
                more = b""
            finally:
                os.set_blocking(fd, True)
            return keys.SEQUENCES.get(chunk + more, "esc")
        return keys.key_name(chunk)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _last_verdict(root: Path) -> str:
    store = LedgerStore(root)
    verdict = "—"
    for record in store.records():
        if record.get("event") == "gate_decision":
            payload = record.get("payload", {})
            if isinstance(payload, dict):
                verdict = "blocked" if payload.get("block") else "verified"
    return verdict


def _build(root: Path, settings: Settings, state: State) -> Any:
    theme, ascii_only = resolve(state.theme_name, ascii_only=state.ascii_only)
    state.ascii_only = ascii_only
    header = widgets.header(
        theme,
        mode=settings.strictness,
        agent=(next(iter(detected_agents(root)), "none")),
        project=root.name or str(root),
        lang=state.lang,
        last_verdict=_last_verdict(root),
        ascii_only=ascii_only,
    )
    if state.screen is not None:
        body = render_screen(state.screen, root, settings, state.lang, theme, ascii_only)
    else:
        body = widgets.menu(theme, selected=state.selected, lang=state.lang, narrow=state.narrow)
    parts: list[Any] = [header, body]
    if state.help:
        parts.append(widgets.help_overlay(theme, state.lang))
    parts.append(widgets.footer(theme, state.lang))
    return widgets.stack(parts)


def detected_agents(root: Path) -> set[str]:
    """Return detected agent ids (kept tiny; avoids importing adapters twice)."""
    from aiproof.adapters import detect_all

    return {a.id for a in detect_all(root)}


def _static(root: Path, settings: Settings, state: State) -> None:
    """Fallback for non-TTY: print the menu once."""
    theme, _ = resolve(state.theme_name, ascii_only=True)
    from rich.console import Console

    console = Console()
    console.print(
        widgets.header(
            theme,
            mode=settings.strictness,
            agent="none",
            project=root.name or str(root),
            lang=state.lang,
            last_verdict=_last_verdict(root),
            ascii_only=True,
        )
    )
    console.print(widgets.menu(theme, selected=state.selected, lang=state.lang))
    console.print(widgets.footer(theme, state.lang))


def run_tui(*, ascii_only: bool = False, no_anim: bool = False) -> int:
    """Run the interactive TUI; returns a process exit code."""
    root = paths.project_root()
    settings = load_settings(root)
    state = State(lang=detect_language(), theme_name=settings.theme, ascii_only=ascii_only)

    try:
        from rich.console import Console
        from rich.live import Live
    except ModuleNotFoundError:
        _static(root, settings, state)
        return 0

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        _static(root, settings, state)
        return 0

    console = Console()
    state.narrow = console.width < 80
    try:
        with Live(
            _build(root, settings, state),
            console=console,
            screen=True,
            auto_refresh=False,
            transient=False,
        ) as live:
            while True:
                key = _read_key()
                action = keys.action_for(key) or key
                state.narrow = console.width < 80
                if action == "quit":
                    break
                if action == "back" and state.screen is not None:
                    state.screen = None
                elif action == "up" and state.screen is None:
                    state.selected = (state.selected - 1) % len(widgets.MENU)
                elif action == "down" and state.screen is None:
                    state.selected = (state.selected + 1) % len(widgets.MENU)
                elif action == "home":
                    state.selected = 0
                elif action == "end" and state.screen is None:
                    state.selected = len(widgets.MENU) - 1
                elif action == "lang":
                    cycle = [c for c in KNOWN_LANGS if c in available()]
                    if cycle:
                        state.lang = cycle[(cycle.index(state.lang) + 1) % len(cycle)]
                elif action == "theme":
                    state.theme_name = THEME_CYCLE[
                        (THEME_CYCLE.index(state.theme_name) + 1) % len(THEME_CYCLE)
                    ]
                elif action == "help":
                    state.help = not state.help
                elif action.startswith("quick") and state.screen is None:
                    index = int(action[-1]) - 1
                    if 0 <= index < len(widgets.MENU):
                        state.selected = index
                elif action == "select" and state.screen is None:
                    screen = widgets.MENU[state.selected][0]
                    if screen == "exit":
                        break
                    state.screen = screen
                live.update(_build(root, settings, state), refresh=True)
    except KeyboardInterrupt:
        pass
    return 0
