"""TUI: themes, layout-independent keys, widgets and screens (smoke)."""

from __future__ import annotations

from pathlib import Path

from aiproof.config import Settings
from aiproof.tui import keys, widgets
from aiproof.tui.logo import banner, logo
from aiproof.tui.screens import RENDERERS, render
from aiproof.tui.theme import THEMES, force_ascii, get_theme, resolve


def test_themes_present() -> None:
    assert {"green", "mono", "amber"} <= set(THEMES)
    assert get_theme("nope").name == "green"


def test_cyrillic_keys_map_by_position() -> None:
    assert keys.action_for("ц") == "up"
    assert keys.action_for("ы") == "down"
    assert keys.action_for("й") == "quit"
    assert keys.action_for("w") == "up"


def test_escape_sequences_map() -> None:
    assert keys.key_name(b"\x1b[A") == "up"
    assert keys.key_name(b"\r") == "enter"
    assert keys.SEQUENCES[b"\x1b[1~"] == "home"
    assert keys.SEQUENCES[b"\x1b[4~"] == "end"


def test_read_utf8_char_multibyte() -> None:
    """The POSIX reader must consume all UTF-8 bytes of a Cyrillic key."""
    import os

    from aiproof.tui.app import _read_utf8_char

    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, "ц".encode())
        assert _read_utf8_char(read_fd) == "ц".encode()
        os.write(write_fd, b"q")
        assert _read_utf8_char(read_fd) == b"q"
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_ascii_fallback(monkeypatch) -> None:
    monkeypatch.setenv("LC_ALL", "C")
    assert isinstance(force_ascii(True), bool)
    assert force_ascii(True) is True


def test_logo_and_banner() -> None:
    theme = get_theme("green")
    assert "AIPROOF" in logo(theme).plain.replace(" ", "").upper()
    assert banner(theme).plain


def test_resolve_mono_when_no_color(monkeypatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    theme, _ascii = resolve("green")
    assert theme.name == "mono"


def test_menu_has_all_entries() -> None:
    theme = get_theme("green")
    table = widgets.menu(theme, selected=0, lang="en")
    assert table.row_count == len(widgets.MENU)


def test_ascii_safe_replaces_symbols() -> None:
    from aiproof.tui.theme import ascii_safe

    assert ascii_safe("✓ ● ❯ · — ↑") == "v * > - - ^"
    assert ascii_safe("ok Привет") == "ok Привет"


def test_data_table_uses_ascii_box() -> None:
    from rich import box

    theme = get_theme("green")
    assert widgets.data_table("t", theme=theme, ascii_only=True).box is box.ASCII
    assert widgets.data_table("t", theme=theme, ascii_only=False).box is box.HEAVY_HEAD


def test_menu_ascii_marker() -> None:
    from rich.console import Console

    console = Console(record=True, width=100, force_terminal=False)
    console.print(widgets.menu(get_theme("mono"), selected=0, lang="en", ascii_only=True))
    text = console.export_text()
    assert ">" in text
    assert "❯" not in text


def test_header_renders() -> None:
    theme = get_theme("green")
    panel = widgets.header(
        theme,
        mode="enforce",
        agent="claude-code",
        project="demo",
        lang="en",
        last_verdict="verified",
    )
    assert panel is not None


def test_all_screens_render(tmp_path: Path) -> None:
    settings = Settings()
    theme = get_theme("green")
    for screen in RENDERERS:
        output = render(screen, tmp_path, settings, "en", theme, True)
        assert output is not None
