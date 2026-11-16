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
