"""Turkish claim-phrase pack (draft)."""

from __future__ import annotations

from aiproof.claims.model import ClaimType as C
from aiproof.claims.model import Rule

CODE = "tr"
STOPWORDS = ("ve", "testler", "commit", "push", "dosya", "tamamlandı", "geçti")
NEG = ("değil", "henüz", "yok", "olmadı")
HEDGE = ("olmalı", "muhtemelen", "belki", "gibi")

RULES: tuple[Rule, ...] = (
    Rule(C.TESTS_PASS, (r"tüm testler geçti", r"testler geç(?:ti|iyor)"), NEG, HEDGE),
    Rule(C.COMMITTED, (r"commit ettim", r"commitledim"), NEG, HEDGE),
    Rule(C.PUSHED, (r"push ettim", r"pushladım"), NEG, HEDGE),
    Rule(
        C.FILE_WRITTEN,
        (
            r"dosya[^.\n]{0,20}oluştur",
            r"oluştur[^.\n]{0,20}dosya",
            r"(?:oluşturdum|oluşturuldu|yazdım)[^\n]{0,40}\.[A-Za-z0-9]{1,6}",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.FILE_CHANGED, (r"güncelledim", r"değiştirdim"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"sildim",), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"tamamlandı", r"bitti", r"hazır"), NEG, HEDGE),
    Rule(C.TESTS_ADDED, (r"test ekledim", r"yeni testler", r"testler eklendi"), NEG, HEDGE),
    Rule(C.BUILD_PASSES, (r"derleme başarılı", r"build başarılı", r"derleme geçti"), NEG, HEDGE),
    Rule(
        C.LINT_PASSES,
        (
            r"lint (?:temiz|başarılı|geçti)",
            r"linter temiz",
        ),
        NEG,
        HEDGE,
    ),
    Rule(
        C.BUG_FIXED,
        (r"bug[^.\n]{0,20}düzelttim", r"hatayı düzelttim", r"bug düzeltildi"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.DEPENDENCY_INSTALLED,
        (
            r"bağımlılık kurdum",
            r"paket kurdum",
            r"bağımlılık yüklendi",
        ),
        NEG,
        HEDGE,
    ),
    Rule(
        C.MIGRATION_RUN,
        (
            r"migration çalıştırdım",
            r"migrasyon çalıştırdım",
            r"migration uygulandı",
        ),
        NEG,
        HEDGE,
    ),
)
