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
    Rule(C.FILE_WRITTEN, (r"\barchivo[^.\n]{0,20}\bcreado\b", r"\bcreé\b"), NEG, HEDGE),
    Rule(C.FILE_CHANGED, (r"\bmodifiqué\b", r"\bactualicé\b"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"\beliminé\b", r"\bborré\b"), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"\blisto\b", r"\bterminado\b", r"\bcompletado\b"), NEG, HEDGE),
)
