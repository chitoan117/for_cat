#!/bin/sh
# Operator-run only after secure FastAPI profile is running on127.0.0.1:8000.
set -eu
if [ "${1:-}" != "--apply" ]; then
  printf '%s\n' 'PLAN ONLY. After operator Tailscale login/device approval, review grants and run:' \
    'tailscale serve --bg --https=443 http://127.0.0.1:8000' \
    'tailscale serve status'
  exit 0
fi
tailscale serve --bg --https=443 http://127.0.0.1:8000
tailscale serve status
