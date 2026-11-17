"""English claim-phrase pack (source of truth for the pack format)."""

from __future__ import annotations

from aiproof.claims.model import ClaimType as C
from aiproof.claims.model import Rule

CODE = "en"
STOPWORDS = ("the", "and", "tests", "committed", "pushed", "file", "done", "pass")

NEG = ("not ", "didn't", "did not", "haven't", "have not", "wasn't", "isn't", "no ", "never")
HEDGE = ("should", "probably", "might", "may ", "seems", "appears", "hopefully", "i think")

RULES: tuple[Rule, ...] = (
    Rule(
        C.TESTS_PASS,
        (
            r"\ball tests? (?:pass|passed|are passing|passing)\b",
            r"\btests? (?:pass|passed|are passing)\b",
            r"\b\d+\s+(?:tests?\s+)?(?:passed|passing)\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.TESTS_ADDED, (r"\badded tests?\b", r"\bnew tests?\b", r"\btests? added\b"), NEG, HEDGE),
    Rule(
        C.COMMITTED,
        (
            r"\bcommitted\b",
            r"\bi(?:'ve| have) committed\b",
            r"\bcommitted as\b",
            r"\bcreated commit\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.PUSHED, (r"\bpushed\b", r"\bi(?:'ve| have) pushed\b"), NEG, HEDGE),
    Rule(
        C.FILE_WRITTEN,
        (
            r"\b(?:created|wrote|written|added)\b[^.\n]{0,40}\bfile\b",
            r"\bfile\b[^.\n]{0,20}\b(?:created|written)\b",
            # "Created src/app.py." without the word "file".
            r"\b(?:created|wrote|written)\b[^\n]{0,40}\b[\w/\\-]+\.[A-Za-z0-9]{1,6}\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.FILE_CHANGED, (r"\b(?:updated|modified|edited|changed)\b",), NEG, HEDGE),
    Rule(
        C.FILE_DELETED, (r"\b(?:deleted|removed)\b[^.\n]{0,30}\bfile\b", r"\bdeleted\b"), NEG, HEDGE
    ),
    Rule(
        C.BUILD_PASSES,
        (r"\bbuild (?:passes|succeeds|is green|works)\b", r"\bbuilds? (?:ok|fine|green)\b"),
        NEG,
        HEDGE,
    ),
    Rule(C.LINT_PASSES, (r"\blint (?:passes|is clean|ok)\b", r"\blinting passes\b"), NEG, HEDGE),
    Rule(
        C.BUG_FIXED,
        (r"\b(?:fixed|resolved)\b[^.\n]{0,20}\bbug\b", r"\bbug\b[^.\n]{0,20}\bfixed\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.FEATURE_DONE,
        (r"\bdone\b", r"\bcompleted\b", r"\bimplemented\b", r"\bfinished\b"),
        NEG,
        HEDGE,
    ),
    Rule(C.DEPENDENCY_INSTALLED, (r"\binstalled\b", r"\badded dependency\b"), NEG, HEDGE),
    Rule(
        C.MIGRATION_RUN,
        (r"\bmigration\b[^.\n]{0,20}\b(?:ran|run|applied)\b", r"\bran\b[^.\n]{0,20}\bmigration\b"),
        NEG,
        HEDGE,
    ),
)
