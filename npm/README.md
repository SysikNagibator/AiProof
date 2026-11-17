# aiproof-sysik (npm wrapper)

A tiny launcher that downloads the correct **AiProof by SYSIK** binary for your platform,
**verifies its SHA-256 against the release `SHA256SUMS`**, and exposes the `aiproof` command.

> **Not published on npm yet** (verified 2026-11-17). Until it is, install from GitHub:
> `pipx install "git+https://github.com/SysikNagibator/AiProof.git@v0.1.0"`, or run this
> wrapper from a clone with `node npm/install.js`.

Once published:

```sh
npm install -g aiproof-sysik
aiproof --version      # AiProof 0.1.0 by SYSIK
```

## How it works

* `install.js` runs on `postinstall`, picks
  `AiProof_{Linux,macOS,Win}_{x64,arm64}_<version>[.exe]`, fetches it together with
  `SHA256SUMS`, and refuses to write anything if the hash does not match.
* `bin/aiproof.js` is the launcher. It executes the verified binary under `vendor/`, or falls
  back to a system `aiproof` (e.g. installed with `pipx`) if the download was skipped.

Published binaries: Linux x64, Linux arm64, macOS x64, macOS arm64 and Windows x64. Windows
arm64 is **not** built yet; the installer then prints a clear message and leaves a system
`aiproof` usable.

## Configuration

| variable | effect |
| --- | --- |
| `AIPROOF_VERSION` | override the release tag (default `v<package version>`) |
| `AIPROOF_BASE_URL` | override the download base (default GitHub Releases) |
| `AIPROOF_SKIP_DOWNLOAD=1` | do not download a binary (use a system install) |

## Prefer pipx?

The npm wrapper is optional. Once the Python package is on PyPI, `pipx install aiproof-sysik`
gives the same `aiproof` command without any download step. Today, install from GitHub:
`pipx install "git+https://github.com/SysikNagibator/AiProof.git@v0.1.0"`.

MIT © SYSIK.
