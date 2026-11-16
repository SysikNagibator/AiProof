"""German claim-phrase pack (draft)."""

from __future__ import annotations

from aiproof.claims.model import ClaimType as C
from aiproof.claims.model import Rule

CODE = "de"
STOPWORDS = ("und", "tests", "committet", "gepusht", "datei", "fertig", "bestehen")
NEG = ("nicht ", "noch nicht", "kein ")
HEDGE = ("sollte", "wahrscheinlich", "vielleicht", "scheint")

RULES: tuple[Rule, ...] = (
    Rule(
        C.TESTS_PASS,
        (r"\balle tests bestehen\b", r"\btests (?:bestehen|laufen durch)\b"),
        NEG,
        HEDGE,
    ),
    Rule(C.COMMITTED, (r"\b(?:habe )?committet\b", r"\bcommit erstellt\b"), NEG, HEDGE),
    Rule(C.PUSHED, (r"\bgepusht\b",), NEG, HEDGE),
    Rule(C.FILE_WRITTEN, (r"\bdatei[^.\n]{0,20}\berstellt\b", r"\berstellt\b"), NEG, HEDGE),
    Rule(C.FILE_CHANGED, (r"\bgeändert\b", r"\baktualisiert\b"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"\bgelöscht\b",), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"\bfertig\b", r"\babgeschlossen\b", r"\bimplementiert\b"), NEG, HEDGE),
)
