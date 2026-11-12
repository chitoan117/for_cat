#!/bin/bash
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo 'Run with sudo on Jetson; enter the password only in your Jetson terminal.' >&2
  exit 1
fi
ROOT=/home/toan/for_cat/evidence/uart_20261110
RULE=/etc/udev/rules.d/99-forcat-uart.rules
test -c /dev/ttyTHS1
test "$(readlink -f /sys/class/tty/ttyTHS1/device)" = /sys/devices/70006040.serial
test -f "$ROOT/99-forcat-uart.rules"
if [ -e "$RULE" ] && ! cmp -s "$RULE" "$ROOT/99-forcat-uart.rules"; then
  echo 'Existing UART rule differs; nothing changed.' >&2
  exit 1
fi
if [ ! -e "$ROOT/system_before.txt" ]; then
  {
    systemctl is-enabled nvgetty.service || true
    systemctl is-active nvgetty.service || true
    stat -c '%a %U %G' /dev/ttyTHS1
  } > "$ROOT/system_before.txt"
fi
# J6 application UART only. Keep kernel debug console ttyS0 untouched.
systemctl disable --now nvgetty.service
install -m 0644 "$ROOT/99-forcat-uart.rules" "$RULE"
udevadm control --reload-rules
udevadm trigger --action=change --subsystem-match=tty --sysname-match=ttyTHS1
chgrp dialout /dev/ttyTHS1
chmod 0660 /dev/ttyTHS1
if systemctl is-active --quiet nvgetty.service; then
  echo 'nvgetty remains active; do not connect TX/RX yet.' >&2
  exit 1
fi
if fuser /dev/ttyTHS1 >/dev/null 2>&1; then
  echo 'UART still has another owner; do not connect TX/RX yet.' >&2
  exit 1
fi
echo 'UART READY: ttyTHS1, dialout, 0660; no getty owner.'
ls -l /dev/ttyTHS1
