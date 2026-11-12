#!/bin/sh
set -eu
root=$(realpath "$(dirname "$0")/..")
exec "${PYTHON:-python3}" "$root/scripts/validate_esp32_stack.py" "$@"
