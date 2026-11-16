#!/usr/bin/env bash
# Build a single-file AiProof binary with PyInstaller.
#
# Usage: tools/build_exe.sh [--onefile|--onedir] [--debug]
# Produces dist/AiProof_<OS>_<version>[.exe] and (on non-Windows) a SHA-256 file.
# Requirements: Python 3.11+, the dev extra (pyinstaller), and an installed icon under
# assets/ (see tools/build_icon.py). Runs offline.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="--onefile"
[[ "${1:-}" == "--onedir" ]] && MODE="--onedir"
DEBUG_FLAG=""
[[ "${1:-}" == "--debug" || "${2:-}" == "--debug" ]] && DEBUG_FLAG="--debug=all"

VERSION="$(python -c 'import aiproof; print(aiproof.__version__)')"

case "$(uname -s)" in
  Darwin) OS="macOS" ;;
  Linux)  OS="Linux" ;;
  *)      OS="Unknown" ;;
esac

ICON=""
if [[ "$OS" == "macOS" && -f assets/AiProof.icns ]]; then
  ICON="--icon assets/AiProof.icns"
elif [[ -f assets/AiProof.ico ]]; then
  ICON="--icon assets/AiProof.ico"
fi

echo "Building AiProof $VERSION for $OS ($MODE)"

pyinstaller \
  --name "AiProof_${OS}_${VERSION}" \
  --clean --noconfirm \
  "$MODE" \
  $ICON \
  $DEBUG_FLAG \
  --collect-data aiproof \
  --hidden-import rich \
  --hidden-import wcwidth \
  --hidden-import tomli_w \
  --console \
  src/aiproof/__main__.py

cd dist
if [[ "$OS" == "Linux" || "$OS" == "macOS" ]]; then
  if ! command -v sha256sum >/dev/null 2>&1; then
    echo "note: sha256sum not found; skipping checksum" >&2
  else
    sha256sum "AiProof_${OS}_${VERSION}" > "AiProof_${OS}_${VERSION}.sha256"
    echo "checksum: $(cat "AiProof_${OS}_${VERSION}.sha256")"
  fi
fi
echo "done: dist/AiProof_${OS}_${VERSION}"
