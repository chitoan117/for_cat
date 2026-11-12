#!/bin/sh
# Build only. Explicit new output path; never replaces the running binary.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
OUT="${1-}"
case "$OUT" in /*) ;; *) echo 'Usage: sh scripts/build_cat_dog_trt.sh /absolute/new/binary' >&2; exit 2;; esac
test -d "$(dirname -- "$OUT")" || { echo 'Output parent does not exist' >&2; exit 2; }
test ! -e "$OUT" || { echo 'Refusing to overwrite output binary' >&2; exit 2; }
CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-10.2}"
command -v "${CXX:-g++}" >/dev/null
pkg-config --exists opencv4
"${CXX:-g++}" -std=c++14 -O2 -pthread "$ROOT/jetson/ai/cat_dog_trt.cpp" -o "$OUT" \
  $(pkg-config --cflags --libs opencv4) \
  -I/usr/include/aarch64-linux-gnu -I"$CUDA_HOME/include" \
  -L/usr/lib/aarch64-linux-gnu -L"$CUDA_HOME/lib64" -lnvinfer -lcudart
sha256sum "$OUT"
