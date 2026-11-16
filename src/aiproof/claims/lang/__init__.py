"""Claim language packs: registry, detection and lookup."""

from __future__ import annotations

import re
from types import ModuleType

from aiproof.claims.lang import (
    de,
    en,
    es,
    fr,
    ja,
    ko,
    pt,
    ru,
    tr,
    uk,
    zh,
)

_MODULES: tuple[ModuleType, ...] = (en, ru, uk, de, es, fr, pt, zh, ja, ko, tr)

LANG_PACKS: dict[str, ModuleType] = {m.CODE: m for m in _MODULES}

# Unicode script ranges used for cheap language detection.
_SCRIPT_HINTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("zh", re.compile(r"[\u4e00-\u9fff]")),
    ("ja", re.compile(r"[\u3040-\u30ff]")),
    ("ko", re.compile(r"[\uac00-\ud7af]")),
    ("ru", re.compile(r"[\u0400-\u04ff]")),
)
_UK_MARKERS = ("і", "ї", "є", "ґ", "тести проходять", "закомітив")


def detect_language(text: str) -> str | None:
    """Return a best-effort language code, or ``None`` when uncertain."""
    if not text:
        return None
    for code, rx in _SCRIPT_HINTS:
        if rx.search(text):
            if code == "ru" and any(m in text for m in _UK_MARKERS):
                return "uk"
            return code
    lowered = text.lower()
    tokens = set(re.findall(r"[^\W\d_]+", lowered, re.UNICODE))
    scores: dict[str, int] = {}
    for code, module in LANG_PACKS.items():
        stopwords = getattr(module, "STOPWORDS", ())
        scores[code] = sum(1 for w in stopwords if w in tokens)
    best = max(scores, key=lambda c: scores[c])
    return best if scores[best] > 0 else None


def pack(code: str) -> ModuleType | None:
    """Return the module for a language code, or ``None``."""
    return LANG_PACKS.get(code)


def all_codes() -> tuple[str, ...]:
    """Return every supported language code."""
    return tuple(LANG_PACKS.keys())
