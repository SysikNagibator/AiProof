"""Ukrainian claim-phrase pack (draft)."""

from __future__ import annotations

from aiproof.claims.model import ClaimType as C
from aiproof.claims.model import Rule

CODE = "uk"
STOPWORDS = ("і", "тести", "закомітив", "запушив", "файл", "готово", "проходять")
NEG = ("не ", "ще не", "не зробив")
HEDGE = ("вроде", "мабуть", "напевно", "повинно", "здається")

RULES: tuple[Rule, ...] = (
    Rule(C.TESTS_PASS, (r"\bусі тести проходять\b", r"\bтести проходять\b"), NEG, HEDGE),
    Rule(C.COMMITTED, (r"\bзакомітив\w*\b", r"\bзробив коміт\b"), NEG, HEDGE),
    Rule(C.PUSHED, (r"\bзапушив\w*\b",), NEG, HEDGE),
    Rule(
        C.FILE_WRITTEN,
        (
            r"\bфайл[^.\n]{0,20}\bстворен\w*\b",
            r"\bстворив\w* файл\b",
            r"\b(?:створив|написав)\w*\b[^\n]{0,40}\b[\w/\\-]+\.[A-Za-z0-9]{1,6}\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.FILE_CHANGED, (r"\bоновив\w*\b", r"\bзмінив\w*\b"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"\bвидалив\w*\b",), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"\bготово\b", r"\bзроблено\b", r"\bзавершено\b"), NEG, HEDGE),
    Rule(C.TESTS_ADDED, (r"\bдодав тести\b", r"\bнові тести\b", r"\bтести додано\b"), NEG, HEDGE),
    Rule(
        C.BUILD_PASSES,
        (r"\bзбірка проходить\b", r"\bзбирається\b", r"\bбілд (?:ок|зелений)\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.LINT_PASSES,
        (
            r"\bлінт\w* прох\w*\b",
            r"\bлінтер (?:чисто|ок)\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(
        C.BUG_FIXED,
        (r"\bвиправив\w*[^.\n]{0,20}\bбаг\b", r"\bбаг[^.\n]{0,20}\bвиправл\w*\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.DEPENDENCY_INSTALLED,
        (
            r"\bвстановив\w* залежніст\w*\b",
            r"\bвстановив\w* пакет\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(
        C.MIGRATION_RUN,
        (
            r"\bзапустив\w* міграці\w*\b",
            r"\bміграці\w* застосован\w*\b",
        ),
        NEG,
        HEDGE,
    ),
)
