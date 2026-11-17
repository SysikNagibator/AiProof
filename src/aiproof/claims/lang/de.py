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
    Rule(
        C.FILE_WRITTEN,
        (
            r"\bdatei[^.\n]{0,20}\berstellt\b",
            r"\berstellt\b[^.\n]{0,20}\bdatei\b",
            r"\b(?:erstellt|geschrieben)\b[^\n]{0,40}\b[\w/\\-]+\.[A-Za-z0-9]{1,6}\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.FILE_CHANGED, (r"\bgeändert\b", r"\baktualisiert\b"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"\bgelöscht\b",), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"\bfertig\b", r"\babgeschlossen\b", r"\bimplementiert\b"), NEG, HEDGE),
    Rule(
        C.TESTS_ADDED,
        (r"\btests? hinzugefügt\b", r"\bneue tests?\b", r"\btests? ergänzt\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.BUILD_PASSES,
        (r"\bbuild (?:ist )?(?:grün|erfolgreich|ok)\b", r"\berfolgreich gebaut\b"),
        NEG,
        HEDGE,
    ),
    Rule(C.LINT_PASSES, (r"\blint(?:ing)? (?:ist )?(?:sauber|ok|grün)\b",), NEG, HEDGE),
    Rule(
        C.BUG_FIXED,
        (r"\bbug[^.\n]{0,20}\b(?:behoben|gefixt)\b", r"\bfehler[^.\n]{0,20}\bbehoben\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.DEPENDENCY_INSTALLED,
        (r"\b(?:abhängigkeit|paket|bibliothek)\w* installiert\b",),
        NEG,
        HEDGE,
    ),
    Rule(
        C.MIGRATION_RUN, (r"\bmigration\w*[^.\n]{0,20}\b(?:ausgeführt|angewendet)\b",), NEG, HEDGE
    ),
)
