"""French claim-phrase pack (draft)."""

from __future__ import annotations

from aiproof.claims.model import ClaimType as C
from aiproof.claims.model import Rule

CODE = "fr"
STOPWORDS = ("et", "tests", "commit", "push", "fichier", "terminé", "passent")
NEG = ("ne ", "pas ", "pas encore")
HEDGE = ("devrait", "probablement", "peut-être", "semble")

RULES: tuple[Rule, ...] = (
    Rule(C.TESTS_PASS, (r"\btous les tests passent\b", r"\bles tests passent\b"), NEG, HEDGE),
    Rule(C.COMMITTED, (r"\bj'ai commité\b", r"\bcommité\b"), NEG, HEDGE),
    Rule(C.PUSHED, (r"\bj'ai poussé\b", r"\bpoussé\b"), NEG, HEDGE),
    Rule(C.FILE_WRITTEN, (r"\bfichier[^.\n]{0,20}\bcréé\b", r"\bcréé\b"), NEG, HEDGE),
    Rule(C.FILE_CHANGED, (r"\bmodifié\b", r"\bmis à jour\b"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"\bsupprimé\b",), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"\bterminé\b", r"\bfini\b", r"\bimplémenté\b"), NEG, HEDGE),
)
