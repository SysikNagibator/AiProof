"""Layout-independent key mapping (physical key positions).

Russian/other layouts must work by position: physical W/S/Q/L/T keys map to the
same actions even when the layout produces Cyrillic characters.
"""

from __future__ import annotations

ACTIONS: dict[str, str] = {
    # movement
    "w": "up",
    "ц": "up",
    "W": "up",
    "Ц": "up",
    "s": "down",
    "ы": "down",
    "S": "down",
    "Ы": "down",
    "up": "up",
    "down": "down",
    "home": "home",
    "end": "end",
    # navigation
    "enter": "select",
    "esc": "back",
    "backspace": "back",
    "q": "quit",
    "й": "quit",
    "Q": "quit",
    "Й": "quit",
    "l": "lang",
    "д": "lang",
    "L": "lang",
    "Д": "lang",
    "t": "theme",
    "е": "theme",
    "T": "theme",
    "Е": "theme",
    "r": "refresh",
    "к": "refresh",
    "R": "refresh",
    "К": "refresh",
    "?": "help",
    "/": "filter",
    "1": "quick1",
    "2": "quick2",
    "3": "quick3",
    "4": "quick4",
    "5": "quick5",
    "6": "quick6",
    "7": "quick7",
    "8": "quick8",
    "9": "quick9",
}

# Raw escape sequences -> symbolic key names.
SEQUENCES: dict[bytes, str] = {
    b"\x1b[A": "up",
    b"\x1b[B": "down",
    b"\x1b[H": "home",
    b"\x1b[F": "end",
    b"\r": "enter",
    b"\n": "enter",
    b"\x1b": "esc",
    b"\x7f": "backspace",
    b"\x08": "backspace",
}


def action_for(name: str) -> str | None:
    """Return the action for a symbolic key name, or ``None``."""
    return ACTIONS.get(name)


def key_name(raw: bytes) -> str:
    """Map a raw byte sequence to a symbolic key name."""
    if raw in SEQUENCES:
        return SEQUENCES[raw]
    try:
        char = raw.decode("utf-8")
    except UnicodeDecodeError:
        return ""
    return ACTIONS.get(char, char)
