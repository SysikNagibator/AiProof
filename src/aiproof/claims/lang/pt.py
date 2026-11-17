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
    Rule(
        C.FILE_WRITTEN,
        (
            r"\barquivo[^.\n]{0,20}\bcriado\b",
            r"\b(?:criei|criado|escrevi)\b[^.\n]{0,20}\barquivo\b",
            r"\b(?:criei|escrevi)\b[^\n]{0,40}\b[\w/\\-]+\.[A-Za-z0-9]{1,6}\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.FILE_CHANGED, (r"\batualizei\b", r"\bmodifiquei\b"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"\bdeletei\b", r"\bremovi\b"), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"\bpronto\b", r"\bconcluído\b", r"\bfinalizado\b"), NEG, HEDGE),
    Rule(
        C.TESTS_ADDED,
        (r"\badicionei testes\b", r"\bnovos testes\b", r"\btestes adicionados\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.BUILD_PASSES,
        (r"\ba compilação passa\b", r"\bcompila (?:bem|com sucesso)\b", r"\bbuild (?:ok|verde)\b"),
        NEG,
        HEDGE,
    ),
    Rule(C.LINT_PASSES, (r"\blint(?:er)? (?:limpo|ok)\b",), NEG, HEDGE),
    Rule(
        C.BUG_FIXED,
        (r"\bcorrigi[^.\n]{0,20}\bbug\b", r"\bbug[^.\n]{0,20}\bcorrigido\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.DEPENDENCY_INSTALLED,
        (
            r"\binstalei (?:a )?(?:dependência|biblioteca)\b",
            r"\bdependência instalada\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(
        C.MIGRATION_RUN,
        (
            r"\bexecutei[^.\n]{0,20}\bmigração\b",
            r"\bmigração[^.\n]{0,20}\baplicada\b",
        ),
        NEG,
        HEDGE,
    ),
)
