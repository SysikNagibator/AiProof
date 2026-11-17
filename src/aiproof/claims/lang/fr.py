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
    Rule(
        C.FILE_WRITTEN,
        (
            r"\bfichier[^.\n]{0,20}\bcréé\b",
            r"\b(?:créé|écrit)\b[^.\n]{0,20}\bfichier\b",
            r"\b(?:créé|écrit)\b[^\n]{0,40}\b[\w/\\-]+\.[A-Za-z0-9]{1,6}\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.FILE_CHANGED, (r"\bmodifié\b", r"\bmis à jour\b"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"\bsupprimé\b",), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"\bterminé\b", r"\bfini\b", r"\bimplémenté\b"), NEG, HEDGE),
    Rule(
        C.TESTS_ADDED,
        (r"\bajouté des tests\b", r"\bnouveaux tests\b", r"\btests ajoutés\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.BUILD_PASSES,
        (
            r"\bla compilation (?:passe|réussit)\b",
            r"\bcompile (?:bien|correctement)\b",
            r"\bbuild (?:ok|vert)\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.LINT_PASSES, (r"\blint(?:er)? (?:propre|ok)\b",), NEG, HEDGE),
    Rule(
        C.BUG_FIXED,
        (r"\bcorrigé[^.\n]{0,20}\b(?:bug|bogue)\b", r"\bréparé[^.\n]{0,20}\bbug\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.DEPENDENCY_INSTALLED,
        (
            r"\binstallé (?:la )?(?:dépendance|bibliothèque)\b",
            r"\bdépendance installée\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(
        C.MIGRATION_RUN,
        (
            r"\bexécuté[^.\n]{0,20}\bmigration\b",
            r"\bmigration[^.\n]{0,20}\bappliquée\b",
        ),
        NEG,
        HEDGE,
    ),
)
