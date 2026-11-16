"""Brazilian Portuguese claim-phrase pack (draft)."""

from __future__ import annotations

from aiproof.claims.model import ClaimType as C
from aiproof.claims.model import Rule

CODE = "pt"
STOPWORDS = ("e", "testes", "commit", "push", "arquivo", "pronto", "passam")
NEG = ("não ", "sem ", "ainda não")
HEDGE = ("deveria", "provavelmente", "talvez", "parece")

RULES: tuple[Rule, ...] = (
    Rule(C.TESTS_PASS, (r"\btodos os testes passam\b", r"\bos testes passam\b"), NEG, HEDGE),
    Rule(C.COMMITTED, (r"\bfiz commit\b", r"\bcommitei\b"), NEG, HEDGE),
    Rule(C.PUSHED, (r"\bfiz push\b", r"\benviei\b"), NEG, HEDGE),
    Rule(C.FILE_WRITTEN, (r"\barquivo[^.\n]{0,20}\bcriado\b", r"\bcriei\b"), NEG, HEDGE),
    Rule(C.FILE_CHANGED, (r"\batualizei\b", r"\bmodifiquei\b"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"\bdeletei\b", r"\bremovi\b"), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"\bpronto\b", r"\bconcluído\b", r"\bfinalizado\b"), NEG, HEDGE),
)
