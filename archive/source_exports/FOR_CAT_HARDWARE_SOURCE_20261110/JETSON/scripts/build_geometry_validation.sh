#!/bin/sh
# Isolated build; existing production source/binary/engine are read-only inputs.
set -eu
root=$(realpath "$(dirname "$0")/..")
out=${1:-}
case "$out" in /*) ;; *) printf '%s\n' 'Usage: sh scripts/build_geometry_validation.sh /absolute/NEW/binary' >&2; exit 2;; esac
test -d "$(dirname "$out")"
test ! -e "$out"
test -d "${TMPDIR:-/tmp}"
build=$(mktemp -d "${TMPDIR:-/tmp}/for-cat-geometry-build.XXXXXX")
cuda=${CUDA_HOME:-/usr/local/cuda-10.2}
cxx=${CXX:-g++}
pkg-config --exists opencv4
inc=$(pkg-config --variable=includedir opencv4)
set -- -std=c++14 -O1 -g -pthread -fno-omit-frame-pointer
case "${SANITIZER:-none}" in
  none) ;;
  address,undefined) set -- "$@" -fsanitize=address,undefined ;;
  thread) set -- "$@" -fsanitize=thread ;;
  *) printf '%s\n' 'Invalid SANITIZER' >&2; exit 2;;
esac
printf 'Build scratch: %s\n' "$build"
sha256sum "$root/jetson/ai/cat_dog_trt" "$root/models/tensorrt/yolov8n_320_fp16.engine" "$root/jetson/ai/cat_dog_trt.cpp"
# Included, frozen production TU is compiled under its established warning policy.
# All additive code is separately strict-built below; no duplicated TRT decoder.
"$cxx" "$@" -Wno-deprecated-declarations -isystem "$inc" -I"$cuda/include" \
  -c "$root/jetson/ai/shadow/geometry_detector.cpp" -o "$build/detector.o"
for name in behavior_shadow shadow_json geometry_tool; do
  "$cxx" "$@" -Wall -Wextra -Werror -Wconversion -Wshadow -Wpedantic -Wno-deprecated-declarations \
    -isystem "$inc" "-DFOR_CAT_REPO=\"$root\"" -c "$root/jetson/ai/shadow/$name.cpp" -o "$build/$name.o"
done
"$cxx" "$@" "$build/detector.o" "$build/behavior_shadow.o" "$build/shadow_json.o" "$build/geometry_tool.o" \
  -o "$out" $(pkg-config --libs opencv4) -L"$cuda/lib64" -lnvinfer -lcudart -lcrypto
sha256sum "$root/jetson/ai/cat_dog_trt" "$root/models/tensorrt/yolov8n_320_fp16.engine" "$root/jetson/ai/cat_dog_trt.cpp"
printf 'Standalone binary: %s\n' "$out"
