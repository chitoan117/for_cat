#!/bin/sh
# Passive diagnostics. The ONLY write option is explicit --save, under evidence/jetson/.
set -u
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
MODE="${1:-}"
if [ "$#" -gt 1 ] || { [ -n "$MODE" ] && [ "$MODE" != '--save' ] && [ "$MODE" != '--stdout-only' ]; }; then
  echo 'Usage: sh scripts/m3_check_jetson.sh [--save]' >&2
  exit 2
fi
if [ "$MODE" = '--save' ]; then
  if [ ! -d "$ROOT/evidence" ]; then
    echo 'Missing project evidence directory; verify you are using the bring-up pack.' >&2
    exit 2
  fi
  mkdir -p "$ROOT/evidence/jetson"
  FILE="$ROOT/evidence/jetson/$(date -u +%Y%m%dT%H%M%SZ)_m3_diagnostics_$$.log"
  (set -C; : > "$FILE") || exit 2
  sh "$0" --stdout-only 2>&1 | tee "$FILE"
  echo "Saved diagnostic output (not an M3 pass): $FILE"
  exit 0
fi
echo 'M3 PREPARATION DIAGNOSTICS — does not validate hardware or advance milestone'
date -u '+UTC %Y-%m-%dT%H:%M:%SZ'
sh "$ROOT/scripts/check_jetson_env.sh"
echo '--- USB inventory ---'
if command -v lsusb >/dev/null 2>&1; then lsusb; else echo 'lsusb unavailable (not installed automatically)'; fi
echo '--- network interfaces (no configuration changes) ---'
if command -v ip >/dev/null 2>&1; then
  ip -brief address
elif command -v ifconfig >/dev/null 2>&1; then
  ifconfig
else
  echo 'network diagnostic command unavailable'
fi
echo 'No webcam frames, serial frames, GPU runtime, sensors or actuators were started.'
