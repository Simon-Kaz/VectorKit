#!/usr/bin/env bash
#
# Run the test suite using the project venv, whether or not it is activated.
# Used by the pre-push git hook (where the venv is not on PATH) and by CI.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -x ".venv/bin/pytest" ]]; then
  exec .venv/bin/pytest -q "$@"
elif command -v pytest >/dev/null 2>&1; then
  # Activated venv or CI where pytest is already on PATH.
  exec pytest -q "$@"
else
  echo "pytest not found. Run 'make setup' to create the venv first." >&2
  exit 1
fi
