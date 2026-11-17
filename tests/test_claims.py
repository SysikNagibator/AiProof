"""Claim extraction: multilingual, negation, hedging, params."""

from __future__ import annotations

from aiproof.claims.extractor import extract_claims, has_claim
from aiproof.claims.model import ClaimType


def test_english_tests_pass() -> None:
    claims = extract_claims("All tests pass now.")
    assert has_claim(claims, ClaimType.TESTS_PASS)


def test_claim_count_extracted() -> None:
    claims = extract_claims("42 tests passed")
    assert claims[0].params.get("count") == 42


def test_committed_hash() -> None:
    claims = extract_claims("committed as abc1234")
    assert has_claim(claims, ClaimType.COMMITTED)
    assert claims[0].params.get("hash") == "abc1234"


def test_file_written_files() -> None:
    claims = extract_claims("created file config.py and it works")
    written = [c for c in claims if c.type is ClaimType.FILE_WRITTEN]
    assert written and "config.py" in written[0].params.get("files", [])


def test_negation_suppresses_claim() -> None:
    assert not has_claim(extract_claims("I have not committed anything"), ClaimType.COMMITTED)
    assert not has_claim(extract_claims("я не закоммитил"), ClaimType.COMMITTED)


def test_hedge_suppresses_claim() -> None:
    assert not has_claim(extract_claims("I think all tests pass"), ClaimType.TESTS_PASS)


def test_russian_tests_pass() -> None:
    claims = extract_claims("все тесты проходят")
    assert claims[0].language == "ru"
    assert has_claim(claims, ClaimType.TESTS_PASS)


def test_chinese_tests_pass() -> None:
    claims = extract_claims("测试全部通过")
    assert claims[0].language == "zh"


def test_hedged_english_phrase_no_claim() -> None:
    assert extract_claims("the tests should pass") == []


def test_many_repeated_claims_scale_linearly() -> None:
    """Regression: dedupe used to be O(n^2) and took seconds on long input."""
    import time

    text = "тесты проходят " * 10000
    start = time.perf_counter()
    claims = extract_claims(text)
    elapsed = time.perf_counter() - start
    assert len(claims) == 10000
    assert elapsed < 2.0, f"extraction too slow: {elapsed:.2f}s"


def test_negation_only_applies_to_its_own_clause() -> None:
    """Regression: ±40-char substring negation suppressed unrelated clauses."""
    assert has_claim(extract_claims("All tests pass, no errors."), ClaimType.TESTS_PASS)
    assert has_claim(extract_claims("All tests pass. You should review."), ClaimType.TESTS_PASS)
    assert has_claim(
        extract_claims("Todas las pruebas pasan, sin errores.", ("es",)), ClaimType.TESTS_PASS
    )
    assert has_claim(
        extract_claims("Todos os testes passam, sem erros.", ("pt",)), ClaimType.TESTS_PASS
    )
    assert has_claim(extract_claims("모든 테스트 통과, 문제없음", ("ko",)), ClaimType.TESTS_PASS)


def test_may_date_is_not_a_hedge() -> None:
    claims = extract_claims("May 12 tests passed")
    assert has_claim(claims, ClaimType.TESTS_PASS)


def test_japanese_is_detected_before_chinese() -> None:
    text = "テストはすべて通過。コミットしました。プッシュしました。"
    claims = extract_claims(text)
    assert {c.type for c in claims} == {
        ClaimType.TESTS_PASS,
        ClaimType.COMMITTED,
        ClaimType.PUSHED,
    }
    assert {c.language for c in claims} == {"ja"}


def test_nearest_number_wins_over_issue_reference() -> None:
    claims = extract_claims("Fixes #123: all 12 tests passed")
    assert [c.params.get("count") for c in claims if c.type is ClaimType.TESTS_PASS] == [12]


def test_every_pack_rule_regex_compiles() -> None:
    """A malformed pattern in any language pack would crash extraction at runtime."""
    import re

    from aiproof.claims import lang

    for code in lang.all_codes():
        module = lang.pack(code)
        assert module is not None
        for rule in module.RULES:
            assert rule.patterns, f"{code}:{rule.claim} has no patterns"
            for pattern in rule.patterns:
                re.compile(pattern, re.IGNORECASE)


def test_draft_packs_extract_core_claims() -> None:
    """Draft (machine-reviewed) packs must still cover their headline phrases."""
    cases = {
        "de": ("Build ist grün, Bug behoben", {ClaimType.BUILD_PASSES, ClaimType.BUG_FIXED}),
        "es": ("La compilación pasa", {ClaimType.BUILD_PASSES}),
        "fr": ("J'ai créé src/app.py", {ClaimType.FILE_WRITTEN}),
        "pt": ("Criei src/app.py", {ClaimType.FILE_WRITTEN}),
        "uk": ("збірка проходить", {ClaimType.BUILD_PASSES}),
        "ja": ("ビルドが成功しました", {ClaimType.BUILD_PASSES}),
        "ko": ("빌드 성공", {ClaimType.BUILD_PASSES}),
        "zh": ("构建成功", {ClaimType.BUILD_PASSES}),
        "tr": ("derleme başarılı", {ClaimType.BUILD_PASSES}),
    }
    for code, (text, expected) in cases.items():
        claims = extract_claims(text, (code,))
        assert expected <= {claim.type for claim in claims}, (code, text, claims)


def test_draft_pack_file_written_ignores_unrelated_created() -> None:
    """`Fehler erstellt` means an error was made, not that a file was written."""
    assert not has_claim(extract_claims("Fehler erstellt", ("de",)), ClaimType.FILE_WRITTEN)
    assert has_claim(extract_claims("Ich habe die Datei erstellt", ("de",)), ClaimType.FILE_WRITTEN)


def test_cjk_bug_fixed_tolerates_spacing() -> None:
    assert has_claim(extract_claims("修复了 bug", ("zh",)), ClaimType.BUG_FIXED)
    assert has_claim(extract_claims("修复了bug", ("zh",)), ClaimType.BUG_FIXED)
    assert has_claim(extract_claims("リント成功", ("ja",)), ClaimType.LINT_PASSES)
    assert has_claim(extract_claims("린트통과", ("ko",)), ClaimType.LINT_PASSES)
