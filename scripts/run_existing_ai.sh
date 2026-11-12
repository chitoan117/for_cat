#!/bin/bash
# Supervise the same detector/tap, without camera contention or GPU restart loops.
set -u
set -o pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEVICE=${FORCAT_CAMERA_DEVICE:-/dev/video0}
waiting=0
while true; do
    reason=""
    if [ ! -c "$DEVICE" ]; then
        reason=CAMERA_NOT_FOUND
    elif fuser "$DEVICE" >/dev/null 2>&1; then
        reason=CAMERA_BUSY
    fi
    if [ -n "$reason" ]; then
        "$ROOT/.venv/jetson-integration/bin/python" "$ROOT/jetson/tools/fc_camera_health.py" "$ROOT/jetson/data/events.db" "$reason"
        if [ "$waiting" -eq 0 ]; then
            printf '%s\n' "ForCat AI waiting: camera absent or already owned ($DEVICE); no duplicate capture"
        fi
        waiting=$(( (waiting + 1) % 30 ))
        sleep 2
        continue
    fi
    waiting=0
    printf '%s\n' 'ForCat starting unchanged TensorRT detector + resilient Python state tap'
    if /usr/bin/stdbuf -oL "$ROOT/jetson/ai/cat_dog_trt" --headless --no-snapshot --device "$DEVICE" |
        "$ROOT/.venv/jetson-integration/bin/python" -u "$ROOT/jetson/tools/fc_ai_tap.py" "$ROOT/jetson/data/events.db"; then
        printf '%s\n' 'ForCat detector stopped; checking camera before recovery'
    else
        printf '%s\n' 'ForCat detector/tap failure; cache will be UNKNOWN/STALE; bounded retry'
    fi
    sleep 5
done
