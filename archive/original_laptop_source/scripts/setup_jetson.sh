#!/bin/sh
# Run manually on a real Jetson. Does not change system Python or JetPack.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PYTHON="${PYTHON_BIN:-python3}"
if ! "$PYTHON" -c 'import sys; print("Detected Python",sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3,10) else 2)' ; then
  echo 'Unsupported Python (<3.10 or missing). Do not upgrade system Python; choose a compatible isolated interpreter.' >&2
  exit 2
fi
VENV="$ROOT/jetson/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  if ! "$PYTHON" -m venv "$VENV"; then
    echo 'Could not create venv. Inspect installed venv support; do not change system Python.' >&2
    exit 2
  fi
fi
if ! "$VENV/bin/python" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 2)' ; then
  echo 'Existing venv has unsupported Python. Do not overwrite it silently.' >&2
  exit 2
fi
"$VENV/bin/python" -m pip --version || {
  echo 'venv pip unavailable. Stop; do not alter system packages.' >&2
  exit 2
}
"$VENV/bin/python" -m pip install -r "$ROOT/jetson/requirements-core.txt"
echo 'Runtime environment prepared. Webcam OpenCV is optional and NOT installed by this script.'
echo 'For tests, explicitly install jetson/requirements-test.txt into this venv, then run python -m pytest.'
