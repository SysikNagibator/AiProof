"""Themes: green (default), mono, amber; NO_COLOR and ASCII fallbacks."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    """A small, calm color palette."""

    name: str
    primary: str
    accent: str
    dim: str
    danger: str
    ok: str
    warn: str


THEMES: dict[str, Theme] = {
    "green": Theme("green", "green", "bright_green", "grey50", "red", "green", "yellow"),
    "mono": Theme("mono", "white", "bright_white", "grey42", "white", "white", "white"),
    "amber": Theme("amber", "dark_orange", "orange1", "grey50", "red", "yellow", "orange3"),
}


def get_theme(name: str) -> Theme:
    """Return a theme by name (falls back to green)."""
    return THEMES.get(name, THEMES["green"])


def no_color() -> bool:
    """Return True when colors must be suppressed."""
    return bool(os.environ.get("NO_COLOR")) or os.environ.get("TERM") == "dumb"


def force_ascii(ascii_only: bool = False) -> bool:
    """Decide whether to use the ASCII-only rendering path."""
    if ascii_only:
        return True
    enc = (os.environ.get("LANG") or "") + (os.environ.get("LC_ALL") or "")
    return "UTF-8" not in enc.upper() and "UTF8" not in enc.upper() and os.name == "nt"


def resolve(name: str, *, ascii_only: bool = False) -> tuple[Theme, bool]:
    """Return ``(theme, use_ascii)`` after applying environment constraints."""
    theme = get_theme(name)
    if no_color():
        theme = get_theme("mono")
    return theme, force_ascii(ascii_only)
