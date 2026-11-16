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
    Rule(C.FILE_WRITTEN, (r"\bфайл[^.\n]{0,20}\bстворен\w*\b", r"\bстворив\w* файл\b"), NEG, HEDGE),
    Rule(C.FILE_CHANGED, (r"\bоновив\w*\b", r"\bзмінив\w*\b"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"\bвидалив\w*\b",), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"\bготово\b", r"\bзроблено\b", r"\bзавершено\b"), NEG, HEDGE),
)
