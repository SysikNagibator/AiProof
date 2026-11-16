"""Russian claim-phrase pack."""

from __future__ import annotations

from aiproof.claims.model import ClaimType as C
from aiproof.claims.model import Rule

CODE = "ru"
STOPWORDS = ("и", "тесты", "закоммитил", "запушил", "файл", "готово", "проходят")

NEG = (
    "не ",
    "не ",
    "ещё не",
    "еще не",
    "не закоммитил",
    "не запушил",
    "не сделал",
    "ничего не",
    "не готово",
)
HEDGE = (
    "вроде",
    "наверное",
    "наверно",
    "должно",
    "может",
    "кажется",
    "похоже",
    "я думаю",
    "вероятно",
)

RULES: tuple[Rule, ...] = (
    Rule(
        C.TESTS_PASS,
        (
            r"\bвсе тесты проходят\b",
            r"\bтесты проходят\b",
            r"\bтесты (?:зелёные|зеленые)\b",
            r"\b\d+\s+тест(?:ов|а)?\s+(?:прошл\w+|проходят|успешно)\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(
        C.TESTS_ADDED,
        (r"\bдобавил тесты\b", r"\bновые тесты\b", r"\bтесты добавлены\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.COMMITTED,
        (r"\bзакоммитил\w*\b", r"\bсделал коммит\b", r"\bкоммит\b[^.\n]{0,20}\bсоздан\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.PUSHED,
        (r"\bзапушил\w*\b", r"\bзапушено\b", r"\bотправил в (?:удалённ|удаленн)\w*\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.FILE_WRITTEN,
        (
            r"\bфайл[^.\n]{0,20}\b(?:создан|записан|написан)\w*\b",
            r"\b(?:создал|записал|написал)\w* файл\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.FILE_CHANGED, (r"\bобновил\w*\b", r"\bизменил\w*\b", r"\bпоправил\w*\b"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"\bудалил\w*\b", r"\bфайл[^.\n]{0,20}\bудал\w*\b"), NEG, HEDGE),
    Rule(
        C.BUILD_PASSES,
        (r"\bсборка прох\w*\b", r"\bсобирается\b", r"\bбилд (?:ок|зелёный|зеленый)\b"),
        NEG,
        HEDGE,
    ),
    Rule(C.LINT_PASSES, (r"\bлинт\w* прох\w*\b", r"\bлинтер (?:чисто|ок)\b"), NEG, HEDGE),
    Rule(
        C.BUG_FIXED,
        (
            r"\bисправил\w*[^.\n]{0,20}\bбаг\b",
            r"\bбаг[^.\n]{0,20}\bисправл\w*\b",
            r"\bпофиксил\w*\b",
        ),
        NEG,
        HEDGE,
    ),
    Rule(
        C.FEATURE_DONE,
        (r"\bготово\b", r"\bсдела\w*\b", r"\bзаверш\w*\b", r"\bреализова\w*\b"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.DEPENDENCY_INSTALLED,
        (r"\bустановил\w* зависимост\w*\b", r"\bпоставил\w* пакет\b"),
        NEG,
        HEDGE,
    ),
    Rule(C.MIGRATION_RUN, (r"\bпрогнал\w* миграци\w*\b", r"\bмиграци\w* примен\w*\b"), NEG, HEDGE),
)
