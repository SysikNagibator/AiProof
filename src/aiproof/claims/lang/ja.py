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
    Rule(
        C.FILE_WRITTEN,
        (
            r"ファイルを作成",
            r"ファイル[^。\n]{0,20}作成",
            r"(?:作成|書き込み)しました[^\n]{0,20}\.[A-Za-z0-9]{1,6}",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.FILE_CHANGED, (r"更新しました", r"変更しました"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"削除しました",), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"完了しました", r"できました", r"実装しました"), NEG, HEDGE),
    Rule(C.TESTS_ADDED, (r"テストを追加しました", r"新しいテスト", r"テスト追加"), NEG, HEDGE),
    Rule(C.BUILD_PASSES, (r"ビルドが成功", r"ビルド成功", r"ビルド通りました"), NEG, HEDGE),
    Rule(C.LINT_PASSES, (r"(?:リント|lint)\s*(?:成功|通過|クリーン)",), NEG, HEDGE),
    Rule(C.BUG_FIXED, (r"バグを修正", r"バグ修正", r"不具合を修正"), NEG, HEDGE),
    Rule(
        C.DEPENDENCY_INSTALLED,
        (
            r"依存関係をインストール",
            r"パッケージをインストール",
        ),
        NEG,
        HEDGE,
    ),
    Rule(
        C.MIGRATION_RUN,
        (
            r"マイグレーションを実行",
            r"マイグレーション適用",
        ),
        NEG,
        HEDGE,
    ),
)
