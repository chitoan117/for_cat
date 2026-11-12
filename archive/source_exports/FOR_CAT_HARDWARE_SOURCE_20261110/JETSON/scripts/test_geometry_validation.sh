#!/bin/sh
set -eu
root=$(realpath "$(dirname "$0")/..")
test -d "${TMPDIR:-/tmp}"
build=$(mktemp -d "${TMPDIR:-/tmp}/for-cat-geometry-tests.XXXXXX")
cxx=${CXX:-g++}
set -- -std=c++14 -O1 -g -pthread -Wall -Wextra -Werror -Wconversion -Wshadow -Wpedantic -fno-omit-frame-pointer
case "${SANITIZER:-none}" in
  none) ;;
  address,undefined) set -- "$@" -fsanitize=address,undefined ;;
  thread) set -- "$@" -fsanitize=thread ;;
  *) exit 2;;
esac
printf 'Test scratch: %s\nSanitizer: %s\n' "$build" "${SANITIZER:-none}"
"$cxx" "$@" "$root/jetson/ai/shadow/behavior_shadow.cpp" "$root/jetson/ai/shadow/shadow_json.cpp" \
  "$root/jetson/ai/shadow/test_geometry_validation.cpp" -o "$build/test_geometry_validation"
"$build/test_geometry_validation"
# Shared-instance concurrency is not supported. TSan targets four independent owners.
if test "${SANITIZER:-none}" = thread; then
  printf '%s\n' 'TSan scope: pure native helpers and independent-owner stress; CUDA/OpenCV workflow excluded.'
  exit 0
fi
sh "$root/scripts/build_geometry_validation.sh" "$build/geometry_validate"
inc=$(pkg-config --variable=includedir opencv4)
"$cxx" "$@" -isystem "$inc" "$root/jetson/ai/shadow/make_geometry_fixture.cpp" \
  -o "$build/make_fixture" $(pkg-config --libs opencv4)
if test "${SANITIZER:-none}" = address,undefined; then
  # LSan process teardown through vendor CUDA/OpenCV libraries is outside scope.
  # Keep ASan/UBSan active for every CLI; pure native checks above also use LSan.
  export ASAN_OPTIONS=detect_leaks=0:halt_on_error=1
  printf '%s\n' 'CLI sanitizer scope: ASan/UBSan; leak scanning only on pure native tests.'
fi
FOR_CAT_GEOMETRY_TOOL="$build/geometry_validate" FOR_CAT_GEOMETRY_FIXTURE="$build/make_fixture" \
  FOR_CAT_GEOMETRY_EVIDENCE="$build/workflow_evidence" python3 "$root/scripts/test_geometry_workflow.py"
printf 'PASS; bounded SYNTHETIC evidence: %s/workflow_evidence\n' "$build"
