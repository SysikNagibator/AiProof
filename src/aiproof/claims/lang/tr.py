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
    Rule(C.FILE_WRITTEN, (r"dosya oluşturuldu", r"oluşturdum"), NEG, HEDGE),
    Rule(C.FILE_CHANGED, (r"güncelledim", r"değiştirdim"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"sildim",), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"tamamlandı", r"bitti", r"hazır"), NEG, HEDGE),
)
