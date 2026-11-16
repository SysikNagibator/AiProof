# Contributing

Thanks for helping make agents honest. This project values **honesty over polish**: a
documented gap beats a claimed feature.

## Ground rules

1. Never trust the agent's text as evidence; never convert `unknown` to `pass`.
2. Never store or print raw secrets — type, location and fingerprint only.
3. The gate reads only pinned settings; an agent can never change them.
4. Never invent hook or CLI APIs. Verify against current docs and record the date.
5. No network calls except the explicit, confirmed update.
6. No marketing numbers without a real bench result.
7. Every user-facing string goes through i18n. Every destructive action confirms and backs up.
8. "AiProof by SYSIK" stays in the README header, `--version`, About, binary info and LICENSE.

If a change cannot satisfy one of these, open an issue to discuss it first.

## Setup

```sh
git clone <repo>
cd aiproof
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

## The loop

```sh
ruff check .            # lint
ruff format .           # format
mypy                    # strict type check over src/aiproof
pytest                  # tests (149 currently)
```

All four must be clean before a PR. CI runs the same on Linux/macOS/Windows for Python
3.11–3.13.

## Adding things

* **A check** — see `docs/CHECKS.md` (positive, negative, edge and Windows-path tests).
* **A language pack** — see `docs/CLAIMS.md`.
* **A UI catalog** — see `docs/I18N.md` and run `tools/gen_catalog_report.py`.
* **An adapter** — read the vendor's *current* docs, then add a registry entry and set
  `status`/`verified` honestly. `verified` requires a date. See `docs/HOOKS.md`.
* **A benchmark scenario** — see `docs/BENCH.md`; regenerate `docs/BENCH_RESULTS.md`.

## Style

* `ruff` (rules in `pyproject.toml`) and `ruff format` define style. Don't fight the formatter.
* British/American spelling does not matter; consistency within a file does.
* Docstrings on public functions. Prefer small pure functions; keep I/O at the edges.
* No `shell=True` with user data. All subprocess calls use argument lists with timeouts.

## Tests

* Unit tests for every check: positive, negative, edge, Windows-path cases.
* Redactor tests use a synthetic corpus of real-looking secrets plus benign look-alikes
  that must not be mangled.
* E2E tests spawn the real hook entrypoints with realistic stdin JSON and assert exit codes
  and JSON output.
* TUI tests render snapshots at widths 60/80/120 per language and theme and cover
  Russian-layout key mapping.

`coverage fail_under = 85` applies to the core package when run with `--cov`.

## Commits and PRs

Use Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`). Small,
focused PRs. Describe the *why* and paste the test output. If you knowingly leave a gap,
list it in the PR body and add it to "Known gaps" in the README.

## Reporting issues

Include your OS, Python version, `aiproof --version`, the failing command and its output,
and `aiproof doctor` output. Never paste real secrets; AiProof redacts its own output, but
your shell history may not.
