#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT=${1:-"$ROOT/.native-build/esp32"}
mkdir -p "$OUT"
${CXX:-g++} -std=c++14 -O2 -Wall -Wextra -Wpedantic -Werror \
  "$ROOT/jetson/device/esp32_bridge.cpp" $(pkg-config --cflags --libs json-c sqlite3) \
  -I"${FORCAT_FIRMWARE_INCLUDE:-$ROOT/esp32/include}" \
  -o "$OUT/esp32_bridge"
${CXX:-g++} -std=c++14 -O2 -Wall -Wextra -Wpedantic -Werror \
  "$ROOT/jetson/device/ai_state_tap.cpp" $(pkg-config --cflags --libs json-c sqlite3) \
  -o "$OUT/ai_state_tap"
printf '%s\n' "Built $OUT/esp32_bridge (default read-only; --dog-warning1 permits only buzzer commands; NO FEED TX)"
