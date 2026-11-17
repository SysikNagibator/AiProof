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
from aiproof.i18n import KNOWN_LANGS, available, detect_language, t
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


def _read_utf8_char(fd: int) -> bytes:
    """Read one (possibly multi-byte UTF-8) character from *fd*.

    A single ``os.read(fd, 1)`` returns only one byte, so a Cyrillic/Greek/CJK
    key (2-4 UTF-8 bytes) would fail to decode and map to no action. Read the
    full sequence based on the lead byte.
    """
    first = os.read(fd, 1)
    if not first:
        return b""
    lead = first[0]
    if lead < 0x80:
        return first
    if 0xC0 <= lead < 0xE0:
        needed = 1
    elif 0xE0 <= lead < 0xF0:
        needed = 2
    elif 0xF0 <= lead < 0xF8:
        needed = 3
    else:
        return first  # invalid lead byte; let key_name handle it
    rest = b""
    while len(rest) < needed:
        chunk = os.read(fd, needed - len(rest))
        if not chunk:
            break
        rest += chunk
    return first + rest


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
        chunk = _read_utf8_char(fd)
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


def _verdict_token(root: Path) -> str:
    """Return ``none``/``blocked``/``verified`` for the last gate decision."""
    store = LedgerStore(root)
    token = "none"
    for record in store.records():
        if record.get("event") == "gate_decision":
            payload = record.get("payload", {})
            if isinstance(payload, dict):
                token = "blocked" if payload.get("block") else "verified"
    return token


def _last_verdict(root: Path, lang: str) -> str:
    """Return the localized last-verdict label."""
    return t(f"status.verdict_{_verdict_token(root)}", lang)


def _build(root: Path, settings: Settings, state: State) -> Any:
    theme, ascii_only = resolve(state.theme_name, ascii_only=state.ascii_only)
    state.ascii_only = ascii_only
    header = widgets.header(
        theme,
        mode=settings.strictness,
        agent=(next(iter(detected_agents(root)), "none")),
        project=root.name or str(root),
        lang=state.lang,
        last_verdict=_last_verdict(root, state.lang),
        ascii_only=ascii_only,
    )
    if state.screen is not None:
        body = render_screen(state.screen, root, settings, state.lang, theme, ascii_only)
    else:
        body = widgets.menu(
            theme,
            selected=state.selected,
            lang=state.lang,
            narrow=state.narrow,
            ascii_only=ascii_only,
        )
    parts: list[Any] = [header, body]
    if state.help:
        parts.append(widgets.help_overlay(theme, state.lang, ascii_only=ascii_only))
    parts.append(widgets.footer(theme, state.lang, ascii_only=ascii_only))
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
            last_verdict=_last_verdict(root, state.lang),
            ascii_only=True,
        )
    )
    console.print(widgets.menu(theme, selected=state.selected, lang=state.lang, ascii_only=True))
    console.print(widgets.footer(theme, state.lang, ascii_only=True))


def apply_action(state: State, action: str) -> bool:
    """Apply one decoded key *action* to *state*.

    Pure state transition (no rendering, no I/O) so every branch is testable.
    Returns ``True`` when the caller should quit the TUI.
    """
    if action == "quit":
        return True
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
            current = cycle.index(state.lang) if state.lang in cycle else -1
            state.lang = cycle[(current + 1) % len(cycle)]
    elif action == "theme":
        try:
            current = THEME_CYCLE.index(state.theme_name)
        except ValueError:
            current = -1  # unknown configured theme -> start at green
        state.theme_name = THEME_CYCLE[(current + 1) % len(THEME_CYCLE)]
    elif action == "help":
        state.help = not state.help
    elif action.startswith("quick") and state.screen is None:
        try:
            index = int(action[len("quick") :]) - 1
        except ValueError:
            index = -1
        if 0 <= index < len(widgets.MENU):
            state.selected = index
    elif action == "select" and state.screen is None:
        screen = widgets.MENU[state.selected][0]
        if screen == "exit":
            return True
        state.screen = screen
    return False


def run_tui(*, ascii_only: bool = False, no_anim: bool = False) -> int:
    """Run the interactive TUI; returns a process exit code."""
    root = paths.project_root()
    settings = load_settings(root)
    state = State(lang=detect_language(), theme_name=settings.theme, ascii_only=ascii_only)

    try:
        from rich.console import Console
        from rich.live import Live
    except ModuleNotFoundError:  # pragma: no cover - rich is a declared dependency
        print("AiProof TUI requires the 'rich' package; install it with: pip install rich")
        return 1

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
                if apply_action(state, action):
                    break
                live.update(_build(root, settings, state), refresh=True)
    except KeyboardInterrupt:
        pass
    return 0
