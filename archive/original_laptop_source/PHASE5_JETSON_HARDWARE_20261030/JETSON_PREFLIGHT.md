# Jetson read-only preflight — PARTIAL / BLOCKED_AUTH

Date: 2026-10-30. Sources: actual SSH command receipt and LAN GET responses; no remote shell output is invented.

## Executed

```text
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes -o NumberOfPasswordPrompts=0 -o ConnectionAttempts=1 -o ConnectTimeout=10 toan@192.168.123.8 sh -s
stdin: jetson_preflight.sh
```

- Client start/end: `2026-10-30T02:26:52.979055Z` / `02:26:53.187759Z`.
- Exit **255**: `Permission denied (publickey,password)`.
- Evidence: `evidence/jetson_preflight/{command.json,output.log}`; stdin SHA recorded.
- No host-key bypass, password storage or retry. Authentication failed before the read-only script ran.

## What is actually known

| Item | Status / evidence |
|---|---|
| Jetson Nano connected/assembled, SSH available to USER | OWNER_CONFIRMED |
| Shell hostname, architecture/OS, GCC/g++, dependencies, RAM/swap/disk | BLOCKED; not measured |
| AI/API/Bridge systemd active state, current PIDs/executables | BLOCKED; no successful `systemctl`/`/proc` read |
| Actual sole serial owner | BLOCKED; no successful `fuser`; PID3989 remains historical |
| Existing R1 result file at owner-specified path | OWNER_CONFIRMED prior PASS; current attachment NOT_RUN |
| Sensor image on Jetson staging | OWNER_CONFIRMED prior MATCH; not rehashed remotely |
| LAN API health/readiness | VERIFIED_PASS HTTP reachability; health 200, API/database report READY, overall ready=false |
| Bridge state via API | VERIFIED_PASS observation: heartbeat age 0.126→0.047 s, but ESP32_BAD_TELEMETRY and telemetry_usable_now=false |
| USB via API | Reports `/dev/ttyACM0`, VID/PID `1a86:55d3`, serial `5C85066678`; matches expected serial string, not independent udev/fuser verification |

Bridge API boot ID: `9dadfe2d-c005-4c1c-88a5-af0624fefea1`. The API reports `serial_connected=true`, TX disabled and actuator execution false; none proves electrical output isolation or exclusive port ownership.

## Clock discrepancy to inspect, not correct automatically

Client HTTP receipt is about `02:29Z`, while server JSON says `09:29...+00:00` / `09:29...Z`, approximately **+7 hours**. This could be clock/UTC labeling inconsistency; root cause NOT_RUN. Preserve both timestamps, use reported monotonic progression for the observed heartbeat comparison, and review `date -u` plus `timedatectl status` on Jetson. Do not set clock/NTP/services in this session.

## Exact next collector

`jetson_preflight.sh` is read-only: system identity/resources, `systemctl --user show/is-active`, `/proc/PID/exe`, USB/udev/fuser, listening sockets, bounded existing journals, exact R1 result and staged sensor image size/hash. Each command records UTC and exit code; overall script exit 0 does not mean every command passed.

USER-run transfer/preflight instructions are in `NEXT_USER_ACTIONS.md`. No serial/security/eFuse maintenance scripts are part of this preflight execution.
