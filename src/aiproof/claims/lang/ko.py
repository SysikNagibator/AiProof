"""Korean claim-phrase pack (draft)."""

from __future__ import annotations

from aiproof.claims.model import ClaimType as C
from aiproof.claims.model import Rule

CODE = "ko"
STOPWORDS = ("의", "테스트", "커밋", "푸시", "파일", "완료", "통과")
NEG = ("아직", "안 ", "없", "못")
HEDGE = ("아마", "듯", "것 같", "일지도")

RULES: tuple[Rule, ...] = (
    Rule(C.TESTS_PASS, (r"모든 테스트 통과", r"테스트 통과", r"테스트가 통과"), NEG, HEDGE),
    Rule(C.COMMITTED, (r"커밋했습니다", r"커밋했어요"), NEG, HEDGE),
    Rule(C.PUSHED, (r"푸시했습니다",), NEG, HEDGE),
    Rule(
        C.FILE_WRITTEN,
        (
            r"파일 생성",
            r"파일[^.\n]{0,20}생성",
            r"(?:생성|작성)했습니다[^\n]{0,20}\.[A-Za-z0-9]{1,6}",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.FILE_CHANGED, (r"수정했습니다", r"업데이트했습니다"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"삭제했습니다",), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"완료했습니다", r"다 했어요", r"구현했습니다"), NEG, HEDGE),
    Rule(C.TESTS_ADDED, (r"테스트를 추가했습니다", r"새로운 테스트", r"테스트 추가"), NEG, HEDGE),
    Rule(C.BUILD_PASSES, (r"빌드 성공", r"빌드가 통과", r"빌드 통과"), NEG, HEDGE),
    Rule(C.LINT_PASSES, (r"(?:린트|lint)\s*(?:통과|성공)",), NEG, HEDGE),
    Rule(C.BUG_FIXED, (r"버그를 수정", r"버그 수정", r"오류를 수정"), NEG, HEDGE),
    Rule(
        C.DEPENDENCY_INSTALLED,
        (
            r"의존성을 설치",
            r"패키지를 설치",
        ),
        NEG,
        HEDGE,
    ),
    Rule(
        C.MIGRATION_RUN,
        (
            r"마이그레이션을 실행",
            r"마이그레이션 적용",
        ),
        NEG,
        HEDGE,
    ),
)
