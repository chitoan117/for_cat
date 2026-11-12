#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ai=${FORCAT_EXISTING_AI:-$root/jetson/ai}
out=${1:?usage: build_roi_ai_source.sh NEW_ABSOLUTE_BINARY}
test -d "$(dirname "$out")"
test ! -e "$out"
cuda=${CUDA_HOME:-/usr/local/cuda-10.2}
${CXX:-g++} -std=c++14 -O2 -pthread -Wno-deprecated-declarations \
  -I"$ai" -I"$cuda/include" $(pkg-config --cflags opencv4 json-c sqlite3) \
  "$root/jetson/device/roi_ai_source.cpp" -o "$out" \
  $(pkg-config --libs opencv4 json-c sqlite3) -L"$cuda/lib64" -lnvinfer -lcudart
