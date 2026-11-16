# aiproof-sysik (npm wrapper)

A tiny launcher that downloads the correct **AiProof by SYSIK** binary for your platform,
**verifies its SHA-256 against the release `SHA256SUMS`**, and exposes the `aiproof` command.

```sh
npm install -g aiproof-sysik
aiproof --version      # AiProof 0.1.0 by SYSIK
```

## How it works

* `install.js` runs on `postinstall`, picks `AiProof_{Linux,macOS,Win}_<version>[.exe]`, fetches
  it together with `SHA256SUMS`, and refuses to write anything if the hash does not match.
* `bin/aiproof.js` is the launcher. It executes the verified binary under `vendor/`, or falls
  back to a system `aiproof` (e.g. installed with `pipx`) if the download was skipped.

## Configuration

| variable | effect |
| --- | --- |
| `AIPROOF_VERSION` | override the release tag (default `v<package version>`) |
| `AIPROOF_BASE_URL` | override the download base (default GitHub Releases) |
| `AIPROOF_SKIP_DOWNLOAD=1` | do not download a binary (use a system install) |

## Prefer pipx?

The npm wrapper is optional. `pipx install aiproof-sysik` gives the same `aiproof` command
from the Python package and avoids any download step.

MIT © SYSIK.
