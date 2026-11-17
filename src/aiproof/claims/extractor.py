"""Deterministic, multilingual claim extraction from an agent's final message."""

from __future__ import annotations

import re
from bisect import bisect_left, bisect_right

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


# Sentence/clause terminators. Negation or hedging in a *different* clause must not
# suppress a claim ("All tests pass, no errors." is still a tests-pass claim).
_CLAUSE_BREAKS = re.compile(
    r"[.!?;:,\n\u3002\uff01\uff1f\uff1b\uff1a\u3001\uff0c]"
    r"|\b(?:but|however|although|though|yet|"
    r"aber|jedoch|mais|pero|sino|mas|fakat|ama|ancak|"
    r"\u043d\u043e|\u043e\u0434\u043d\u0430\u043a\u043e|\u0430\u043b\u0435|"
    r"\u3067\u3082|\u3057\u304b\u3057|\u305f\u3060\u3057|"
    r"\ud558\uc9c0\ub9cc|\uadf8\ub7ec\ub098|"
    r"\u4f46\u662f|\u4f46|\u4e0d\u8fc7)\b",
    re.IGNORECASE,
)

# A clause without punctuation (e.g. a repeated-phrase flood) would otherwise make
# every negation check scan the whole message. Bounding the context keeps extraction
# linear while still covering a normal sentence around the claim.
_CLAUSE_RADIUS = 200


class _ClauseIndex:
    """Precomputed clause boundaries for one message (linear to build)."""

    __slots__ = ("_ends", "_starts", "_text")

    def __init__(self, text: str) -> None:
        self._text = text
        self._starts: list[int] = []
        self._ends: list[int] = []
        for match in _CLAUSE_BREAKS.finditer(text):
            self._starts.append(match.start())
            self._ends.append(match.end())

    def clause(self, start: int, end: int) -> str:
        """Return the clause containing ``text[start:end]`` (bounded context)."""
        left_index = bisect_right(self._ends, start)
        left = self._ends[left_index - 1] if left_index else 0
        right_index = bisect_left(self._starts, end)
        right = self._starts[right_index] if right_index < len(self._starts) else len(self._text)
        left = max(left, start - _CLAUSE_RADIUS)
        right = min(right, end + _CLAUSE_RADIUS)
        return self._text[left:right]


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    """Case-insensitive token search with word boundaries for ASCII words."""
    lowered = haystack.lower()
    for needle in needles:
        token = needle.strip()
        if not token:
            continue
        if token.isascii() and token.replace("_", "").isalpha():
            # ``may 12`` is a date, not a hedge.
            if token.lower() == "may" and re.search(r"\bmay\s+\d", lowered):
                continue
            if re.search(rf"(?<!\w){re.escape(token)}(?!\w)", haystack, re.IGNORECASE):
                return True
        elif token.lower() in lowered:
            return True
    return False


def _nearest_number(text: str, start: int, end: int, radius: int = 80) -> int | None:
    """Return the number closest to the claim span (inside it wins)."""
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    best: int | None = None
    best_key: tuple[int, int] | None = None
    for match in NUM_RE.finditer(text, lo, hi):
        num_start, num_end = match.span(1)
        if num_start >= start and num_end <= end:
            distance = 0
        elif num_end <= start:
            distance = start - num_end
        else:
            distance = num_start - end
        key = (distance, abs(num_start - start))
        if best_key is None or key < best_key:
            best_key = key
            best = int(match.group(1))
    return best


def _params(claim_type: ClaimType, text: str, start: int, end: int) -> dict[str, object]:
    params: dict[str, object] = {}
    if claim_type in _NUMBERED:
        count = _nearest_number(text, start, end)
        if count is not None:
            params["count"] = count
    window = _window(text, start, end, radius=80)
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
    clauses = _ClauseIndex(text)
    for code in codes:
        module = lang.pack(code)
        if module is None:
            continue
        for rule in module.RULES:
            for pattern in rule.patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    clause = clauses.clause(match.start(), match.end())
                    if _has_any(clause, rule.negations) or _has_any(clause, rule.hedges):
                        continue
                    key = (str(rule.claim), match.start(), match.end())
                    if key in seen:
                        continue
                    seen.add(key)
                    found.append(
                        Claim(
                            type=rule.claim,
                            text=match.group(0),
                            span=(match.start(), match.end()),
                            language=code,
                            params=_params(rule.claim, text, match.start(), match.end()),
                        )
                    )
    return _dedupe(found)


def _dedupe(claims: list[Claim]) -> list[Claim]:
    """Drop claims of the same type whose spans overlap an earlier, wider one.

    Claims are sorted by start (wider first on ties), so any earlier kept claim
    of the same type starts at or before the current claim. Overlap therefore
    reduces to ``current.start < max_end_of_kept`` for that type, giving a
    linear pass instead of an O(n^2) pairwise comparison.
    """
    claims.sort(key=lambda c: (c.span[0], -(c.span[1] - c.span[0])))
    kept: list[Claim] = []
    max_end: dict[ClaimType, int] = {}
    for claim in claims:
        start, end = claim.span
        if start < max_end.get(claim.type, -1):
            continue
        kept.append(claim)
        max_end[claim.type] = max(max_end.get(claim.type, end), end)
    return kept


def has_claim(claims: list[Claim], claim_type: ClaimType) -> bool:
    """Return True when at least one claim of the given type exists."""
    return any(c.type is claim_type for c in claims)
