#!/bin/sh
# USER runs on Jetson via MobaXterm. Read-only inventory, no device/service action.
set -eu
D=/home/toan/for_cat/evidence/esp32_backup_20261029
if [ ! -d "$D" ]; then printf '%s\n' "Evidence directory not found: $D"; exit 2; fi
printf '\n=== BRIDGE: USER SCOPE (read-only) ===\n'
systemctl --user is-active for-cat-esp32-bridge.service || true
printf '\n=== BRIDGE: SYSTEM SCOPE (read-only) ===\n'
systemctl is-active for-cat-esp32-bridge.service || true
printf '\n=== EXISTING FILES / SIZES ===\n'
find "$D" -type f -printf '%P\t%s bytes\n' | sort
printf '\n=== EXISTING FILE SHA256 ===\n'
find "$D" -type f -exec sha256sum {} \;
printf '\n%s\n' 'INVENTORY_ONLY_NOT_FULL_BACKUP_VALIDATION; NO_SERIAL_OPEN; NO_RESET; NO_FLASH'
