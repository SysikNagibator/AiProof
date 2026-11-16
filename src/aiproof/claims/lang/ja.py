"""Japanese claim-phrase pack (draft)."""

from __future__ import annotations

from aiproof.claims.model import ClaimType as C
from aiproof.claims.model import Rule

CODE = "ja"
STOPWORDS = ("の", "テスト", "コミット", "プッシュ", "ファイル", "完了", "通過")
NEG = ("まだ", "未", "していません", "ない", "ません")
HEDGE = ("はず", "たぶん", "かもしれ", "ようです")

RULES: tuple[Rule, ...] = (
    Rule(C.TESTS_PASS, (r"テストはすべて通過", r"テストが通りました", r"テスト通過"), NEG, HEDGE),
    Rule(C.COMMITTED, (r"コミットしました", r"コミット済み"), NEG, HEDGE),
    Rule(C.PUSHED, (r"プッシュしました",), NEG, HEDGE),
    Rule(C.FILE_WRITTEN, (r"ファイルを作成", r"作成しました"), NEG, HEDGE),
    Rule(C.FILE_CHANGED, (r"更新しました", r"変更しました"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"削除しました",), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"完了しました", r"できました", r"実装しました"), NEG, HEDGE),
)
