# Signing, code signing and release integrity

Two distinct things share the word "signing" here. Keep them separate.

## 1. Receipt signing (data)

**Status: not implemented.** Cryptographic signing of receipts is a **reserved** `[sign]`
extra. `pyproject.toml` declares the `sign` extra (`cryptography>=42`) so the dependency
exists when it lands, and the receipt JSON reserves a `sign` field.

What exists today:

* The ledger is a **hash chain**; `aiproof ledger verify` detects any silent edit.

What is planned (do not claim it works):

* An optional **HMAC** key (OS keychain via `keyring`, else `~/.aiproof/key` with `0600`)
  to make recomputation harder. It would still **not** be a signature of authorship:
  anyone with the key and the ledger could forge. `paths.key_path()` is reserved for it.
* Ed25519 signature over the **chain head** (not each record).
* A public key published with releases so a verifier can confirm the receipt was produced by
  the key holder and was not altered.
* The `sign` field in the JSON receipt and an HTML footer showing verification status.

Until then, receipts prove **internal consistency and non-modification since writing**, not
authorship. State exactly that.

## 2. Binary code signing (distribution)

**Status: not implemented.** No release binaries are signed yet.

### What AiProof produces

PyInstaller single-file builds, named `AiProof_<OS>_<arch>_<ver>` (`Linux`/`macOS`/`Win`,
`x64`/`arm64`, `.exe` on Windows), with icon and version info (publisher **SYSIK**). The
release workflow also produces `SHA256SUMS`. See `tools/build_exe.sh`, `tools/build_exe.bat`
and `.github/workflows/release.yml`.

### Integrity you get today

* `SHA256SUMS` published with every release.
* `aiproof update --check` reads the release metadata; `verify_sha256()` can validate a
  downloaded file against a manifest. The **download/replace/rollback** path and the TUI
  "Yes to install" flow are **not implemented yet** — do not claim them.
* The npm wrapper (`npm/`) verifies the downloaded binary's SHA-256 before use.

### Windows SmartScreen

Unsigned executables trigger SmartScreen's "unknown publisher" warning. Until the build is
code-signed, users may see this; document it and suggest `pipx`/`npm` as alternatives.
Signing requires an EV code-signing certificate (or Azure Trusted Signing) held by SYSIK.

### macOS Gatekeeper

Unsigned/un-notarized binaries trigger Gatekeeper. Notarization requires an Apple Developer
ID and a notarytool submission in the release workflow. Until then, prefer `pipx`.

### When signing is added

1. Add the certificate/secret to the release workflow as encrypted secrets.
2. Sign the `.exe` (signtool), `.app`/binary (codesign) and notarize (notarytool).
3. Publish the public key for **receipt** signing alongside `SHA256SUMS`.
4. Update this document, `docs/DECISIONS.md` (D6) and the README limitations section.

Do not advertise signed releases or signed receipts before this is done.
