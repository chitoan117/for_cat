#!/bin/sh
# OWNER-RUN scaffold only. Default PLAN; does not contain an automatic write path.
# Real read-flash enters ROM/reset, losing HX711 RAM calibration. Review FIRST.
set -eu
if [ "${1:-}" != "--read-backup-owner-confirmed" ]; then
  printf '%s\n' 'PLAN ONLY. Save HX RAM status, isolate servo/pump/buzzer power, confirm serial transport and ROM chip/flash ID first.' \
    'Owner-only: --read-backup-owner-confirmed NEW_FULL_FLASH_FILE'
  exit 0
fi
backup=${2:?NEW full flash output required}
test ! -e "$backup"
unit=for-cat-esp32-bridge.service
active=0
restore() {
  trap - EXIT INT TERM HUP
  if [ "$active" -eq 1 ]; then
    systemctl --user start "$unit"
    systemctl --user is-active --quiet "$unit" || { printf '%s\n' 'BRIDGE_RESTORE_NOT_VERIFIED' >&2; exit 1; }
  else
    state=$(systemctl --user is-active "$unit" || true)
    case "$state" in inactive|failed) :;; *) printf '%s\n' 'ORIGINAL_INACTIVE_BRIDGE_STATE_NOT_RESTORED' >&2;exit 1;; esac
  fi
}
state=$(systemctl --user is-active "$unit" || true)
case "$state" in active) active=1;; inactive|failed) :;; *) printf '%s\n' 'Unknown user unit state; no serial open' >&2;exit 1;; esac
trap restore EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
if [ "$active" -eq 1 ]; then systemctl --user stop "$unit"; fi
state=$(systemctl --user is-active "$unit" || true)
case "$state" in inactive|failed) :;; *) printf '%s\n' 'Bridge not stopped' >&2;exit 1;; esac
# fuser code1 is accepted only WITHOUT diagnostic errors (permissions/device).
err=$(mktemp)
owner_code=0
fuser /dev/ttyACM0 >/dev/null 2>"$err" || owner_code=$?
if [ "$owner_code" -ne 1 ] || [ -s "$err" ]; then cat "$err" >&2; rm -f "$err"; exit 1; fi
rm -f "$err" # own temporary error file only, never project/SQLite/NVS data
py=${ESPTOOL_PYTHON:-/home/toan/for_cat/.venv/jetson-integration/bin/python}
if [ -n "${ESPTOOL_SCRIPT:-}" ]; then
  "$py" "$ESPTOOL_SCRIPT" --chip esp32s3 --port /dev/ttyACM0 read_flash 0x0 0x1000000 "$backup"
else
  "$py" -m esptool --chip esp32s3 --port /dev/ttyACM0 read_flash 0x0 0x1000000 "$backup"
fi
test "$(wc -c < "$backup")" -eq 16777216
sha256sum "$backup"
# EXIT trap restores only a bridge that was active before this session.
