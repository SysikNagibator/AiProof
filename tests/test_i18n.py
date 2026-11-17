"""i18n: key parity for en/ru, placeholder parity, plurals."""

from __future__ import annotations

import re

from aiproof.i18n import _load, available, is_reviewed, plural, t

PLACEHOLDER = re.compile(r"\{(\w+)\}")


def test_ru_covers_en() -> None:
    en = set(_load("en"))
    ru = set(_load("ru"))
    missing = en - ru
    assert not missing, f"missing Russian keys: {sorted(missing)}"


def test_placeholder_parity_en_ru() -> None:
    en = _load("en")
    ru = _load("ru")
    for key, value in en.items():
        if key in ru:
            assert set(PLACEHOLDER.findall(value)) == set(PLACEHOLDER.findall(ru[key])), key


def test_placeholder_parity_all_catalogs() -> None:
    """A wrong placeholder in any language is always a bug."""
    en = _load("en")
    for code in available():
        data = _load(code)
        for key, value in data.items():
            if key in en:
                assert set(PLACEHOLDER.findall(en[key])) == set(PLACEHOLDER.findall(value)), (
                    code,
                    key,
                )


def test_all_catalogs_cover_ui_keys() -> None:
    """Every shipped catalog covers the full English key set (no silent fallbacks)."""
    en = set(_load("en"))
    for code in available():
        missing = en - set(_load(code))
        assert not missing, f"{code} is missing keys: {sorted(missing)}"


def test_fallback_to_english() -> None:
    assert t("tagline", "de")  # de is a draft but tagline exists
    assert t("menu.doctor", "zz")  # unknown -> English


def test_russian_plurals() -> None:
    assert "1 сессия" in plural("sessions", 1, "ru")
    assert "2 сессии" in plural("sessions", 2, "ru")
    assert "5 сессий" in plural("sessions", 5, "ru")


def test_all_catalogs_parse() -> None:
    # A TOML syntax error silently disables a catalog; make that loud.
    for code in available():
        assert _load(code), f"catalog {code} failed to parse or is empty"


def test_available_and_reviewed() -> None:
    codes = available()
    assert "en" in codes and "ru" in codes
    assert is_reviewed("en") and is_reviewed("ru")
    assert not is_reviewed("de")


def test_saved_language_wins_over_locale(tmp_path, monkeypatch) -> None:
    from aiproof import paths
    from aiproof.i18n import detect_language

    monkeypatch.delenv("AIPROOF_LANG", raising=False)
    monkeypatch.setenv("AIPROOF_DATA_DIR", str(tmp_path / "data"))
    path = paths.global_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('language = "ru"\n', encoding="utf-8")
    assert detect_language() == "ru"
