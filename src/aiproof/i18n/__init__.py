"""i18n engine: catalogs, lookup, plural, detection, fallback chain.

Key lookups: requested language -> English. Missing keys are reported by the
`tools/gen_catalog_report.py` report and asserted by tests for en/ru only.
"""

from __future__ import annotations

import locale
import os
import tomllib
from functools import cache
from pathlib import Path
from typing import Any

from aiproof import paths

CATALOG_DIR = Path(__file__).with_name("catalogs")
SOURCE_LANG = "en"

# Languages we ship catalogs for, in menu-cycle order.
KNOWN_LANGS: tuple[str, ...] = (
    "en",
    "ru",
    "uk",
    "de",
    "es",
    "fr",
    "pt_br",
    "zh_cn",
    "ja",
    "ko",
    "tr",
)

_NON_REVIEWED: frozenset[str] = frozenset(
    {"uk", "de", "es", "fr", "pt_br", "zh_cn", "ja", "ko", "tr"}
)


def _flatten(prefix: str, data: dict[str, Any], out: dict[str, str]) -> None:
    for key, value in data.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            _flatten(dotted, value, out)
        else:
            out[dotted] = str(value)


@cache
def _load(code: str) -> dict[str, str]:
    path = CATALOG_DIR / f"{code}.toml"
    if not path.is_file():
        return {}
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError):
        return {}
    raw.pop("meta", None)
    flat: dict[str, str] = {}
    _flatten("", raw, flat)
    return flat


@cache
def _meta(code: str) -> dict[str, Any]:
    """Return a catalog's ``[meta]`` table (empty when missing/invalid)."""
    path = CATALOG_DIR / f"{code}.toml"
    if not path.is_file():
        return {}
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError):
        return {}
    meta = raw.get("meta")
    return meta if isinstance(meta, dict) else {}


def is_reviewed(code: str) -> bool:
    """Return True when a catalog is human-reviewed (not machine-drafted).

    The catalog's own ``[meta] reviewed`` flag is authoritative; if it is absent
    we fall back to the shipped-language list.
    """
    value = _meta(code).get("reviewed")
    if isinstance(value, bool):
        return value
    return code == SOURCE_LANG or code not in _NON_REVIEWED


def available() -> tuple[str, ...]:
    """Return language codes that actually have a catalog file."""
    return tuple(code for code in KNOWN_LANGS if (CATALOG_DIR / f"{code}.toml").is_file())


def _saved_language() -> str | None:
    """Return the language saved by ``aiproof lang``, when valid."""
    path = paths.global_config_path()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return None
    value = data.get("language")
    return value if isinstance(value, str) and value in KNOWN_LANGS else None


def _os_locale() -> str | None:
    for env_key in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(env_key)
        if value:
            return value.split(".")[0].split("_")[0]
    try:
        code = locale.getlocale()[0]
    except (ValueError, TypeError):  # pragma: no cover
        code = None
    return code


def detect_language() -> str:
    """Resolve the effective UI language following the documented order."""
    forced = os.environ.get("AIPROOF_LANG")
    if forced and forced in KNOWN_LANGS:
        return forced
    saved = _saved_language()
    if saved is not None:
        return saved
    raw = _os_locale()
    if raw:
        candidate = raw.lower()
        if candidate in KNOWN_LANGS:
            return candidate
        if candidate == "pt":
            return "pt_br"
        if candidate == "zh":
            return "zh_cn"
    return SOURCE_LANG


def t(message_key: str, lang: str | None = None, **vars_: object) -> str:
    """Translate *message_key*; fall back to English; interpolate ``{named}`` vars."""
    code = lang or detect_language()
    template = _load(code).get(message_key) or _load(SOURCE_LANG).get(message_key) or message_key
    try:
        return template.format(**vars_)
    except (KeyError, IndexError, ValueError):
        return template


# Plural categories per language family.
_ONE_FEW_MANY = frozenset({"ru", "uk"})
_OTHER_ONLY = frozenset({"zh_cn", "ja", "ko", "tr"})


def _plural_category(code: str, n: int) -> str:
    if code in _OTHER_ONLY:
        return "other"
    if code in _ONE_FEW_MANY:
        mod10, mod100 = n % 10, n % 100
        if mod10 == 1 and mod100 != 11:
            return "one"
        if 2 <= mod10 <= 4 and not 12 <= mod100 <= 14:
            return "few"
        return "many"
    return "one" if n == 1 else "other"


def plural(base_key: str, n: int, lang: str | None = None) -> str:
    """Return a pluralized string for ``plural.<base_key>`` using category suffixes."""
    code = lang or detect_language()
    category = _plural_category(code, n)
    return t(f"plural.{base_key}.{category}", code, n=n)
