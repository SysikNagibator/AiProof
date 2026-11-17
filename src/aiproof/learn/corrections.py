"""Corrections: human feedback, stored redacted and de-duplicated.

A correction is never executed directly. ``compile.py`` may turn a correction
into a declarative rule; otherwise it stays advisory text (never enforced).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from aiproof.ledger.store import LedgerStore
from aiproof.redact.redactor import redact_text

# Light-weight topics used for grouping in the CLI/TUI. Purely cosmetic.
_TOPICS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("tests", ("test", "mock", "assert", "pytest", "coverage", "тест", "мок", "провер")),
    ("git", ("commit", "push", "branch", "rebase", "коммит", "пуш", "ветк")),
    ("secrets", ("secret", "token", "key", "password", "секрет", "ключ", "парол")),
    ("style", ("format", "lint", "style", "naming", "стиль", "формат", "имен")),
    ("docs", ("doc", "readme", "comment", "док", "коммент")),
)

_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class Correction:
    """A single recorded correction with a stable, human-friendly id."""

    id: str
    text: str
    session: str = "human"
    topic: str = "other"

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-safe mapping."""
        return {"id": self.id, "text": self.text, "session": self.session, "topic": self.topic}


def normalize(text: str) -> str:
    """Return a comparison key that ignores case and repeated whitespace."""
    return _WS_RE.sub(" ", text.strip()).casefold()


def topic_of(text: str) -> str:
    """Return a coarse topic for grouping (never used for enforcement)."""
    lowered = text.casefold()
    for topic, needles in _TOPICS:
        if any(needle in lowered for needle in needles):
            return topic
    return "other"


def list_corrections(root: Path) -> list[Correction]:
    """Return every recorded correction, de-duplicated in first-seen order."""
    seen: dict[str, Correction] = {}
    for record in LedgerStore(root).records():
        if record.get("event") != "correction":
            continue
        payload = record.get("payload", {})
        if not isinstance(payload, dict):
            continue
        text = str(payload.get("text", "")).strip()
        if not text:
            continue
        key = normalize(text)
        if key in seen:
            continue
        seen[key] = Correction(
            id=f"C{len(seen) + 1:03d}",
            text=text,
            session=str(record.get("session", "human")),
            topic=topic_of(text),
        )
    return list(seen.values())


def record_correction(root: Path, text: str, *, session: str = "human") -> tuple[Correction, bool]:
    """Record *text* (redacted by the ledger) unless it is a duplicate.

    Returns ``(correction, created)``.
    """
    cleaned = _WS_RE.sub(" ", text.strip())
    if not cleaned:
        raise ValueError("correction text is empty")
    # The ledger redacts on append; deduplicate against the value that will
    # actually be stored so a secret-bearing duplicate is recognised too.
    safe_text = redact_text(cleaned)
    existing = {normalize(c.text): c for c in list_corrections(root)}
    key = normalize(safe_text)
    if key in existing:
        return existing[key], False
    record = LedgerStore(root).append(
        "correction",
        {"text": cleaned, "topic": topic_of(cleaned)},
        session=session,
    )
    payload = record.get("payload")
    stored = safe_text
    topic = topic_of(stored)
    if isinstance(payload, dict):
        if isinstance(payload.get("text"), str):
            stored = payload["text"]
            topic = topic_of(stored)
        if isinstance(payload.get("topic"), str):
            topic = payload["topic"]
    correction = Correction(
        id=f"C{len(existing) + 1:03d}",
        text=stored,
        session=session,
        topic=topic,
    )
    return correction, True


def groups(root: Path) -> dict[str, list[Correction]]:
    """Return corrections grouped by topic."""
    out: dict[str, list[Correction]] = {}
    for correction in list_corrections(root):
        out.setdefault(correction.topic, []).append(correction)
    return out


__all__ = [
    "Correction",
    "groups",
    "list_corrections",
    "normalize",
    "record_correction",
    "topic_of",
]
