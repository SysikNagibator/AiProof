#!/usr/bin/env node
"use strict";

// Thin launcher: delegate to the binary downloaded by install.js under vendor/.
// Never bundles the Python tool; never calls the network at runtime.

const { spawnSync } = require("child_process");
const path = require("path");
const fs = require("fs");

function binaryName() {
  return process.platform === "win32" ? "aiproof.exe" : "aiproof";
}

function candidates() {
  const here = path.join(__dirname, "..", "vendor", binaryName());
  return [here];
}

function main() {
  for (const candidate of candidates()) {
    if (fs.existsSync(candidate)) {
      const result = spawnSync(candidate, process.argv.slice(2), { stdio: "inherit" });
      process.exit(result.status === null ? 1 : result.status);
    }
  }
  // Fall back to a system-installed `aiproof` (e.g. pipx) so the shim stays useful.
  const fallback = spawnSync(binaryName(), process.argv.slice(2), { stdio: "inherit" });
  if (fallback.error) {
    console.error(
      "aiproof binary not found. Run `npm rebuild aiproof-sysik` or install with " +
        "`pipx install aiproof-sysik`."
    );
    process.exit(1);
  }
  process.exit(fallback.status === null ? 1 : fallback.status);
}

main();
