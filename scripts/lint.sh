#!/usr/bin/env bash
# Lint & format check for OverlandListener.
# Usage:
#   scripts/lint.sh          # check only (CI mode, exits non-zero if unformatted)
#   scripts/lint.sh --fix    # auto-format in place

set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--fix" ]]; then
    echo "Formatting with black..."
    black src/ tests/ scripts/
    echo "Done."
else
    echo "Checking formatting with black..."
    black --check --diff src/ tests/ scripts/
    echo "All files formatted correctly."
fi
