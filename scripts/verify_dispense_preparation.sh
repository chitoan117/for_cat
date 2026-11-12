#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT="$ROOT/.native-build/esp32"
mkdir -p "$OUT"
FLAGS='-std=c++14 -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined -Wall -Wextra -Wpedantic -Werror'
${CXX:-g++} $FLAGS -I"$ROOT/esp32/include" "$ROOT/esp32/test/dispense_policy.cpp" -o "$OUT/dispense_policy"
"$OUT/dispense_policy"
${CXX:-g++} $FLAGS -I"$ROOT/esp32/include" "$ROOT/jetson/device/test_dispense_35.cpp" -o "$OUT/dispense_35"
"$OUT/dispense_35"
