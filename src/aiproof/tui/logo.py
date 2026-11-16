"""Pixel-style logo with an optional green gradient."""

from __future__ import annotations

from rich.text import Text

from aiproof.tui.theme import Theme

_BLOCK = "██"
_ASCII = "#"

_GRADIENTS: dict[str, tuple[str, str]] = {
    "green": ("green", "bright_green"),
    "amber": ("dark_orange", "orange1"),
    "mono": ("grey62", "white"),
}


def logo(theme: Theme, *, ascii_only: bool = False) -> Text:
    """Return the AiProof wordmark as styled text."""
    if ascii_only:
        return Text("AIPROOF", style=theme.primary)
    start, end = _GRADIENTS.get(theme.name, _GRADIENTS["green"])
    text = Text()
    letters = "AIPROOF"
    for index, letter in enumerate(letters):
        color = start if index < len(letters) / 2 else end
        text.append(letter, style=f"bold {color}")
        if index != len(letters) - 1:
            text.append(" ")
    return text


def banner(theme: Theme, *, ascii_only: bool = False) -> Text:
    """Return a compact pixel banner (two rows of blocks)."""
    if ascii_only:
        return Text(f"{_ASCII * 28}\n  AIPROOF by SYSIK\n{_ASCII * 28}", style=theme.primary)
    top = Text()
    top.append(_BLOCK * 14, style=f"bold {theme.primary}")
    return top
