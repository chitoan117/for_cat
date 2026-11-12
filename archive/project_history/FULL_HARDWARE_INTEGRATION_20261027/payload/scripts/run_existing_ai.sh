#!/bin/bash
# Supervise the same detector/tap, without camera contention or GPU restart loops.
set -u
set -o pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEVICE=${FORCAT_CAMERA_DEVICE:-/dev/video0}
waiting=0
while true; do
    if [ ! -c "$DEVICE" ] || fuser "$DEVICE" >/dev/null 2>&1; then
        if [ "$waiting" -eq 0 ]; then
            printf '%s\n' "ForCat AI waiting: camera absent or already owned ($DEVICE); no duplicate capture"
        fi
        waiting=$(( (waiting + 1) % 30 ))
        sleep 2
        continue
    fi
    waiting=0
    printf '%s\n' 'ForCat starting unchanged TensorRT detector + read-only C++ state tap'
    if /usr/bin/stdbuf -oL "$ROOT/jetson/ai/cat_dog_trt" --headless --no-snapshot --device "$DEVICE" |
        "$ROOT/.native-build/esp32/ai_state_tap" "$ROOT/jetson/data/events.db"; then
        printf '%s\n' 'ForCat detector stopped; checking camera before recovery'
    else
        printf '%s\n' 'ForCat detector/tap failure; cache will be UNKNOWN/STALE; bounded retry'
    fi
    sleep 5
done
