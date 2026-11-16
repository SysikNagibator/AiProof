# Signing, code signing and release integrity

Two distinct things share the word "signing" here. Keep them separate.

## 1. Receipt signing (data)

**Status: not implemented.** Cryptographic signing of receipts is a **reserved** `[sign]`
extra. `pyproject.toml` declares the `sign` extra (`cryptography>=42`) so the dependency
exists when it lands, and the receipt JSON reserves a `sign` field.

What exists today:

* The ledger is a **hash chain**; `aiproof ledger verify` detects any silent edit.
* An optional **HMAC** key (OS keychain via `keyring`, else `~/.aiproof/key` with `0600`)
  makes recomputation harder but is **not** a signature of authorship. Anyone with the key
  and the ledger can still forge. This is documented in `docs/LEDGER.md`.

What is planned (do not claim it works):

* Ed25519 signature over the **chain head** (not each record).
* A public key published with releases so a verifier can confirm the receipt was produced by
  the key holder and was not altered.
* The `sign` field in the JSON receipt and an HTML footer showing verification status.

Until then, receipts prove **internal consistency and non-modification since writing**, not
authorship. State exactly that.

## 2. Binary code signing (distribution)

**Status: not implemented.** No release binaries are signed yet.

### What AiProof produces

PyInstaller single-file builds, named `AiProof_Win_<ver>.exe`, `AiProof_macOS_<ver>` and
`AiProof_Linux_<ver>`, with icon and version info (publisher **SYSIK**). The release
workflow also produces `SHA256SUMS`. See `tools/build_exe.sh`, `tools/build_exe.bat` and
`.github/workflows/release.yml`.

### Integrity you get today

* `SHA256SUMS` published with every release.
* `aiproof update` verifies the release's SHA-256 from the **manifest**, not from a file
  header alone, requires explicit consent, and can roll back.
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
