#!/bin/sh
# Explicit checked arguments; system Python is preserved. Dry-run unless --apply.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PYTHON="${PYTHON_BIN:-python3}"
PYTHONPATH="$ROOT/jetson${PYTHONPATH:+:$PYTHONPATH}" exec "$PYTHON" -m bringup.flash "$@"
