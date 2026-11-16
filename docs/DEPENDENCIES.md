# Dependencies

AiProof is deliberately small. The runtime dependency set is tiny so the tool installs
anywhere and starts fast.

## Runtime

| package | why |
| --- | --- |
| `rich>=13` | the TUI, tables, panels, the bench table, receipts |
| `wcwidth>=0.2.5` | correct width for CJK and combining characters |
| `tomli-w>=1.0.0` | writing TOML (rules, pinned config, global config) |

Standard library only otherwise: `argparse`, `json`, `hashlib`, `subprocess`,
`dataclasses`, `tomllib` (read), `urllib.request` (the explicit update check), `ast`,
`re`, `shlex`, `fnmatch`, `difflib`.

Python **>= 3.11** (uses `tomllib`, `StrEnum`, `datetime.UTC`).

## Optional extras

| extra | packages | purpose |
| --- | --- | --- |
| `sign` | `cryptography>=42` | reserved for ed25519 receipt signing (not implemented yet) |
| `dev` | `pytest`, `pytest-cov`, `ruff`, `mypy`, `pyinstaller` | development and packaging |

Install:

```sh
pip install "aiproof-sysik[sign]"
pip install "aiproof-sysik[dev]"
```

## Why not more

* **No web framework.** The MCP server speaks the stdio protocol over `json` by hand.
* **No async runtime.** Hooks are short-lived processes; a `subprocess` call with a timeout
  is simpler and safer than an event loop.
* **No keyring at import time.** `keyring` is used opportunistically for the optional HMAC
  key and degrades to a `0600` file when absent.
* **No network client.** The only network call is `aiproof update` (and the optional
  once-a-day *check*), implemented with `urllib.request` and an explicit consent step.

## Supply-chain posture

* Version floors are set; no upper caps except where a major rewrite is expected.
* `aiproof update` verifies **SHA-256 from the release manifest**, not just a downloaded
  file header, before replacing anything, and supports rollback.
* CI runs `ruff`, `mypy --strict` and `pytest` on Linux/macOS/Windows for Python 3.11–3.13.

## Dev environment

```sh
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest
```

`mypy` runs in strict mode over `src/aiproof`. The test suite expects `AIPROOF_DATA_DIR` to
point at a temp dir when a test touches the ledger (the provided fixtures do this for you).
