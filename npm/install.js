#!/usr/bin/env node
"use strict";

// Download the correct AiProof binary for this platform and verify its SHA-256 against the
// release manifest BEFORE writing it to vendor/. Nothing is installed on hash mismatch.
//
// Env:
//   AIPROOF_VERSION     override the release tag (default: the version in package.json)
//   AIPROOF_BASE_URL    override the download base (default: GitHub Releases)
//   AIPROOF_SKIP_DOWNLOAD=1  skip entirely (useful when a system `aiproof` exists)

const crypto = require("crypto");
const fs = require("fs");
const https = require("https");
const os = require("os");
const path = require("path");

const pkg = require("./package.json");
const VERSION = process.env.AIPROOF_VERSION || `v${pkg.version}`;
const BASE =
  process.env.AIPROOF_BASE_URL || `https://github.com/SYSIK/aiproof/releases/download/${VERSION}`;

function assetName() {
  const osName = { linux: "Linux", darwin: "macOS", win32: "Win" }[process.platform];
  if (!osName) throw new Error(`unsupported platform: ${process.platform}`);
  const suffix = process.platform === "win32" ? ".exe" : "";
  return `AiProof_${osName}_${pkg.version}${suffix}`;
}

function get(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, { headers: { "User-Agent": "aiproof-npm" } }, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          res.resume();
          return resolve(get(res.headers.location));
        }
        if (res.statusCode !== 200) {
          res.resume();
          return reject(new Error(`GET ${url} -> ${res.statusCode}`));
        }
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => resolve(Buffer.concat(chunks)));
      })
      .on("error", reject);
  });
}

function sha256(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

async function main() {
  if (process.env.AIPROOF_SKIP_DOWNLOAD === "1") {
    console.log("aiproof-sysik: download skipped (AIPROOF_SKIP_DOWNLOAD=1)");
    return;
  }

  let asset;
  try {
    asset = assetName();
  } catch (err) {
    console.warn(`aiproof-sysik: ${err.message}; skipping binary download`);
    return;
  }

  const vendor = path.join(__dirname, "vendor");
  const target = path.join(vendor, process.platform === "win32" ? "aiproof.exe" : "aiproof");

  try {
    console.log(`aiproof-sysik: downloading ${asset}`);
    const [binary, sums] = await Promise.all([get(`${BASE}/${asset}`), get(`${BASE}/SHA256SUMS`)]);
    const expected = sums
      .toString("utf8")
      .split("\n")
      .map((line) => line.trim().split(/\s+/))
      .filter((parts) => parts.length === 2 && parts[1].endsWith(asset))
      .map((parts) => parts[0])[0];
    if (!expected) {
      throw new Error(`no checksum for ${asset} in SHA256SUMS`);
    }
    const actual = sha256(binary);
    if (actual !== expected) {
      throw new Error(`checksum mismatch for ${asset} (expected ${expected}, got ${actual})`);
    }
    fs.mkdirSync(vendor, { recursive: true });
    fs.writeFileSync(target, binary, { mode: 0o755 });
    console.log(`aiproof-sysik: installed verified binary -> ${target}`);
  } catch (err) {
    // Never fail the install hard: a system `aiproof` (pipx) may be present.
    console.warn(
      `aiproof-sysik: could not fetch a release binary (${err.message}).\n` +
        "Install the CLI with `pipx install aiproof-sysik` instead."
    );
  }
}

main();
