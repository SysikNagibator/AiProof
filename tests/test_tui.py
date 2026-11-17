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


# --------------------------------------------------------------------------- #
# state machine (pure) + non-interactive runner
# --------------------------------------------------------------------------- #
def test_apply_action_navigation() -> None:
    from aiproof.tui.app import State, apply_action

    state = State()
    assert apply_action(state, "up") is False
    assert state.selected == len(widgets.MENU) - 1
    assert apply_action(state, "down") is False
    assert state.selected == 0
    assert apply_action(state, "end") is False
    assert state.selected == len(widgets.MENU) - 1
    assert apply_action(state, "home") is False
    assert state.selected == 0
    assert apply_action(state, "bogus") is False
    assert apply_action(state, "quit") is True


def test_apply_action_quick_select_and_bounds() -> None:
    from aiproof.tui.app import State, apply_action

    state = State()
    assert apply_action(state, "quick3") is False
    assert state.selected == 2
    assert apply_action(state, "quick99") is False
    assert state.selected == 2
    assert apply_action(state, "quickx") is False
    assert state.selected == 2
    state.screen = "dashboard"
    assert apply_action(state, "quick4") is False
    assert state.selected == 2


def test_apply_action_screens() -> None:
    from aiproof.tui.app import State, apply_action

    state = State()
    assert apply_action(state, "select") is False
    assert state.screen == widgets.MENU[0][0]
    # Movement is ignored while a screen is open.
    before = state.selected
    assert apply_action(state, "down") is False
    assert state.selected == before
    assert apply_action(state, "back") is False
    assert state.screen is None
    assert apply_action(state, "back") is False

    state.screen = None
    state.selected = len(widgets.MENU) - 1
    assert widgets.MENU[state.selected][0] == "exit"
    assert apply_action(state, "select") is True


def test_apply_action_lang_theme_help() -> None:
    from aiproof.tui.app import State, apply_action

    state = State(lang="en", theme_name="green")
    assert apply_action(state, "lang") is False
    assert state.lang != "en"
    assert apply_action(state, "theme") is False
    assert state.theme_name == "mono"
    assert apply_action(state, "help") is False
    assert state.help is True
    assert apply_action(state, "help") is False
    assert state.help is False

    unknown = State(lang="zz", theme_name="chartreuse")
    assert apply_action(unknown, "lang") is False
    assert unknown.lang == "en"
    assert apply_action(unknown, "theme") is False
    assert unknown.theme_name == "green"


def test_build_and_verdict_helpers(tmp_path: Path, monkeypatch) -> None:
    from aiproof.ledger.store import LedgerStore
    from aiproof.tui import app

    monkeypatch.setenv("AIPROOF_DATA_DIR", str(tmp_path / "data"))
    state = app.State(screen="dashboard")
    built = app._build(tmp_path, Settings(), state)
    assert built is not None
    assert app._verdict_token(tmp_path) == "none"
    assert app._last_verdict(tmp_path, "en")

    store = LedgerStore(tmp_path)
    store.append("gate_decision", {"block": True}, session="s1")
    assert app._verdict_token(tmp_path) == "blocked"
    assert "blocked" in app._last_verdict(tmp_path, "en").lower()
    store.append("gate_decision", {"block": False}, session="s1")
    assert app._verdict_token(tmp_path) == "verified"


def test_run_tui_non_tty_prints_static(tmp_path: Path, monkeypatch) -> None:
    from aiproof.tui import app

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIPROOF_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    assert app.run_tui() == 0
