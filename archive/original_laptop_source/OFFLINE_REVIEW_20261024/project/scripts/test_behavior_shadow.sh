#!/bin/sh
# Build exclusively in scratch. Never rebuilds/replaces cat_dog_trt or its engine.
set -eu
root=$(realpath "$(dirname "$0")/..")
test -d "${TMPDIR:-/tmp}"
build=$(mktemp -d "${TMPDIR:-/tmp}/for-cat-shadow.XXXXXX")
cxx=${CXX:-g++}
set -- -std=c++14 -O1 -g -Wall -Wextra -Werror -Wconversion -Wshadow -Wpedantic -pthread -fno-omit-frame-pointer
case "${SANITIZER:-none}" in
    none) ;;
    address,undefined) set -- "$@" -fsanitize=address,undefined ;;
    thread) set -- "$@" -fsanitize=thread ;;
    *) printf '%s\n' 'SANITIZER must be none, address,undefined, or thread' >&2; exit 2 ;;
esac
src="$root/jetson/ai/shadow"
printf 'Scratch build: %s\nSanitizer: %s\n' "$build" "${SANITIZER:-none}"
"$cxx" --version
"$cxx" "$@" "$src/behavior_shadow.cpp" "$src/shadow_json.cpp" "$src/test_behavior_shadow.cpp" -o "$build/test_behavior_shadow"
"$cxx" "$@" "$src/behavior_shadow.cpp" "$src/shadow_json.cpp" "$src/shadow_demo.cpp" -o "$build/shadow_demo"
"$build/test_behavior_shadow" "$src/test_config.synthetic.json" "$root/jetson/ai/roi_config.example.json"
"$build/shadow_demo" --synthetic "$src/test_config.synthetic.json" > "$build/synthetic_events.jsonl"
python3 - "$build/synthetic_events.jsonl" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    events = [json.loads(line) for line in stream]
assert [e["event_type"] for e in events] == [
    "EATING_START", "EATING_END", "DRINKING_START", "DRINKING_END"]
for start, end in ((events[0], events[1]), (events[2], events[3])):
    assert start["session_id"] == end["session_id"]
    assert start["track_id"] == end["track_id"]
    assert start["end_ms"] is None and start["duration_ms"] is None
    assert end["duration_ms"] == end["end_ms"] - start["start_ms"]
    assert end["emitted_ms"] >= end["end_ms"] >= start["start_ms"]
for event in events:
    assert event["shadow_only"] is True and event["clock"] == "monotonic_ms"
    assert all(event[k] is None for k in ("weight_before", "weight_after", "consumed_grams"))
    assert event["confidence"]["min"] <= event["confidence"]["mean"] <= event["confidence"]["max"]
assert events[0]["roi"] == "FOOD_ROI" and events[2]["roi"] == "WATER_ROI"
print("PASS stdlib JSONL schema/pairing/null-weight smoke (4 synthetic events)")
PY
if "$build/shadow_demo" --synthetic "$root/jetson/ai/roi_config.example.json" > "$build/unconfigured.stdout" 2> "$build/unconfigured.stderr"; then
    printf '%s\n' 'FAIL: unconfigured deployment template was accepted' >&2
    exit 1
fi
printf 'PASS unconfigured template refused; artifacts: %s\n' "$build"
