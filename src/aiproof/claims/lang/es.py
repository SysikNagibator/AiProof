"""Spanish claim-phrase pack (draft)."""

from __future__ import annotations

from aiproof.claims.model import ClaimType as C
from aiproof.claims.model import Rule

CODE = "es"
STOPWORDS = ("y", "pruebas", "commit", "push", "archivo", "listo", "pasan")
NEG = ("no ", "sin ", "aún no", "todavía no")
HEDGE = ("debería", "probablemente", "quizás", "parece")

RULES: tuple[Rule, ...] = (
    Rule(C.TESTS_PASS, (r"\btodas las pruebas pasan\b", r"\blos tests pasan\b"), NEG, HEDGE),
    Rule(C.COMMITTED, (r"\bhice commit\b", r"\bhe hecho commit\b", r"\bcommiteé\b"), NEG, HEDGE),
    Rule(C.PUSHED, (r"\bhice push\b", r"\bsubí\b"), NEG, HEDGE),
    Rule(
        C.FILE_WRITTEN,
        (
            r"\barchivo[^.\n]{0,20}\bcreado\b",
            r"\b(?:creé|creado|escribí)\b[^.\n]{0,20}\barchivo\b",
            r"\b(?:creé|escribí)\b[^\n]{0,40}\b[\w/\\-]+\.[A-Za-z0-9]{1,6}\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.FILE_CHANGED, (r"\bmodifiqué\b", r"\bactualicé\b"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"\beliminé\b", r"\bborré\b"), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"\blisto\b", r"\bterminado\b", r"\bcompletado\b"), NEG, HEDGE),
    Rule(
        C.TESTS_ADDED,
        (r"\bañadí (?:pruebas|tests)\b", r"\bnuevas pruebas\b", r"\bpruebas añadidas\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.BUILD_PASSES,
        (
            r"\bla compilación pasa\b",
            r"\bcompila (?:bien|correctamente)\b",
            r"\bbuild (?:ok|verde)\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.LINT_PASSES, (r"\blint(?:er)? (?:limpio|ok)\b",), NEG, HEDGE),
    Rule(
        C.BUG_FIXED,
        (r"\bcorregí[^.\n]{0,20}\b(?:bug|error)\b", r"\barreglé[^.\n]{0,20}\b(?:bug|error)\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.DEPENDENCY_INSTALLED,
        (
            r"\binstalé (?:la )?(?:dependencia|paquete)\b",
            r"\bdependencia instalada\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(
        C.MIGRATION_RUN,
        (
            r"\bejecuté[^.\n]{0,20}\bmigración\b",
            r"\bmigración[^.\n]{0,20}\baplicada\b",
        ),
        NEG,
        HEDGE,
    ),
)
