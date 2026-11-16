"""Deterministic, multilingual claim extraction from an agent's final message."""

from __future__ import annotations

import re

from aiproof.claims import lang
from aiproof.claims.model import Claim, ClaimType

HASH_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
NUM_RE = re.compile(r"\b(\d{1,6})\b")
FILE_RE = re.compile(r"[\w./\\-]+\.[A-Za-z0-9]{1,6}\b")

_NUMBERED: frozenset[ClaimType] = frozenset({ClaimType.TESTS_PASS, ClaimType.TESTS_ADDED})
_FILEY: frozenset[ClaimType] = frozenset(
    {ClaimType.FILE_WRITTEN, ClaimType.FILE_CHANGED, ClaimType.FILE_DELETED}
)


def _window(text: str, start: int, end: int, radius: int = 40) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)]


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    lowered = haystack.lower()
    return any(n.lower() in lowered for n in needles)


def _params(claim_type: ClaimType, window: str) -> dict[str, object]:
    params: dict[str, object] = {}
    if claim_type in _NUMBERED:
        numbers = NUM_RE.findall(window)
        if numbers:
            params["count"] = int(numbers[0])
    if claim_type in (ClaimType.COMMITTED, ClaimType.PUSHED):
        hashes = HASH_RE.findall(window)
        if hashes:
            params["hash"] = hashes[0]
    if claim_type in _FILEY:
        files = FILE_RE.findall(window)
        if files:
            params["files"] = files
    return params


def extract_claims(text: str, languages: tuple[str, ...] | None = None) -> list[Claim]:
    """Extract claims from *text* using one or more language packs."""
    if not text:
        return []
    if languages is None:
        detected = lang.detect_language(text)
        codes: tuple[str, ...] = (detected,) if detected else lang.all_codes()
    else:
        codes = languages

    found: list[Claim] = []
    seen: set[tuple[str, int, int]] = set()
    for code in codes:
        module = lang.pack(code)
        if module is None:
            continue
        for rule in module.RULES:
            for pattern in rule.patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    window = _window(text, match.start(), match.end())
                    if _has_any(window, rule.negations) or _has_any(window, rule.hedges):
                        continue
                    key = (str(rule.claim), match.start(), match.end())
                    if key in seen:
                        continue
                    seen.add(key)
                    full = _window(text, match.start(), match.end(), radius=80)
                    found.append(
                        Claim(
                            type=rule.claim,
                            text=match.group(0),
                            span=(match.start(), match.end()),
                            language=code,
                            params=_params(rule.claim, full),
                        )
                    )
    return _dedupe(found)


def _dedupe(claims: list[Claim]) -> list[Claim]:
    """Drop claims of the same type whose spans overlap an earlier, wider one."""
    claims.sort(key=lambda c: (c.span[0], -(c.span[1] - c.span[0])))
    kept: list[Claim] = []
    for claim in claims:
        overlap = any(
            k.type == claim.type and not (claim.span[1] <= k.span[0] or claim.span[0] >= k.span[1])
            for k in kept
        )
        if not overlap:
            kept.append(claim)
    return kept


def has_claim(claims: list[Claim], claim_type: ClaimType) -> bool:
    """Return True when at least one claim of the given type exists."""
    return any(c.type is claim_type for c in claims)
