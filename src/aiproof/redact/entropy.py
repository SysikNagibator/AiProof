"""Shannon-entropy heuristic for detecting unlabelled secrets."""

from __future__ import annotations

import math
from collections import Counter

from aiproof.redact.patterns import BENIGN_LOOKALIKES

MIN_LEN = 20
MIN_ENTROPY = 3.5


def shannon_entropy(value: str) -> float:
    """Return the Shannon entropy (bits per symbol) of *value*."""
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((n / length) * math.log2(n / length) for n in counts.values())


def is_benign(token: str) -> bool:
    """Return True when a token is a known high-entropy-but-harmless lookalike."""
    return any(rx.match(token) for rx in BENIGN_LOOKALIKES)


def looks_secret(token: str) -> bool:
    """Return True when *token* is long, high-entropy and not a benign lookalike."""
    if len(token) < MIN_LEN or is_benign(token):
        return False
    return shannon_entropy(token) >= MIN_ENTROPY
