# Claims

A **claim** is a factual statement an agent makes in its final message, e.g. *"all tests
pass"* or *"committed as 9f2c1a4"*. AiProof extracts claims deterministically, then tries
to *falsify* each one against real evidence. A claim is never evidence in itself.

## Model

`src/aiproof/claims/model.py` defines:

```python
class ClaimType(StrEnum):
    (
        COMMITTED,
        PUSHED,
        FILE_WRITTEN,
        FILE_CHANGED,
        FILE_DELETED,
    )
    (
        TESTS_PASS,
        TESTS_ADDED,
        BUILD_PASSES,
        LINT_PASSES,
        BUG_FIXED,
    )
    FEATURE_DONE, DEPENDENCY_INSTALLED, MIGRATION_RUN


class Verdict(StrEnum):
    PASS, FAIL, UNKNOWN
```

`unknown` is a first-class verdict and is **never silently promoted to `pass`**. In
`strict` mode an `unknown` on a key claim blocks; in `enforce` it is recorded; in
`observe`/`warn` it is logged only.

A `Claim` carries `type`, the matched `text` span, optional `params` (hash, file list,
count, suite) and the `language` it was detected in.

## Extraction pipeline

`src/aiproof/claims/extractor.py`:

1. **Candidate detection.** For each language pack, scan the message for phrase patterns
   that map to a claim type.
2. **Negation handling.** Phrases like "not committed yet" / "не закоммитил" /
   "尚未提交" suppress the claim. Negation is checked in a window around the match.
3. **Hedging handling.** "should pass", "вроде проходят", "кажется готово" lower to
   **no claim** (or `unknown`), never to a positive claim. Optimism is not evidence.
4. **Parameter capture.** Numbers near a test claim become `count`; hex runs matching a
   git SHA become `hash`; file-looking tokens become `files`.
5. **Union.** If the language is ambiguous, all packs run and their claims are unioned and
   de-duplicated. Auto-detection is cheap: script ranges + stopword hits.

The extractor is pure: no I/O, no network, deterministic given the same input.

## Multi-language packs

Phrase tables live as data under `src/aiproof/claims/lang/<code>.py`, one module per
language, each exporting `CODE`, `STOPWORDS`, `NEG`, `HEDGE` and `RULES`. Shipped packs:
**en, ru, uk, de, es, fr, pt, zh, ja, ko, tr**. These are separate from the UI catalogs in
`docs/I18N.md` (which use `pt_br`/`zh_cn`) and are tested independently
(`tests/test_claims.py`).

Seed coverage per language (non-exhaustive):

| language | done | tests pass | committed | pushed |
| --- | --- | --- | --- | --- |
| en | done | all tests pass | I committed / committed as | I've pushed |
| ru | готово | все тесты проходят | закоммитил | запушил |
| uk | готово | усі тести проходять | закомітив | запушив |
| de | fertig | alle Tests bestehen | committet | gepusht |
| es | listo | todas las pruebas pasan | hice commit | subí |
| fr | terminé | tous les tests passent | commité | poussé |
| pt_br | pronto | todos os testes passam | fiz commit | enviei |
| zh_cn | 已完成 | 测试全部通过 | 已提交 | 已推送 |
| ja | 完了しました | テストはすべて通過 | コミットしました | プッシュしました |
| ko | 완료했습니다 | 모든 테스트 통과 | 커밋했습니다 | 푸시했습니다 |
| tr | tamamlandı | tüm testler geçti | commit ettim | push ettim |

## Which claims are checkable

* `committed`, `file_changed/written/deleted`, `tests_pass` have dedicated checks
  (`commit_exists`, `file_changed`, `tests_ran`) that produce `pass`/`fail`/`unknown`.
* `bug_fixed`, `feature_done`, `build_passes`, `lint_passes` are only checkable indirectly,
  through the diff and the test run. They are recorded but rarely block on their own.
* Claims with no applicable check produce no `CheckResult` and never block.

## The receipt-block convention

`SKILL.md` asks agents to end a task with a machine-readable block listing claims and the
commands they ran. AiProof parses that block as **additional claims** but **never trusts it
as evidence** — every item is still verified against git, the filesystem and the recorded
test output. A block that lies is caught exactly like a prose lie.

## Adding a language

1. Copy `src/aiproof/claims/lang/en.py` to `<code>.py`.
2. Fill `RULES` with `Rule(claim, patterns, negations=..., hedges=...)`.
3. Register the module in `src/aiproof/claims/lang/__init__.py`.
4. Add positive, negation and hedging tests in `tests/test_claims.py`.

Never map a hedged or negated phrase to a positive claim. If unsure, prefer `unknown`.
