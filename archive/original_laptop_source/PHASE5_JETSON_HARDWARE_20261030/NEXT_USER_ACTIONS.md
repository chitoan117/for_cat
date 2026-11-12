# Next USER actions — unblock preflight/ARM64 first

Date: 2026-10-30. SSH noninteractive auth failed once; LAN GET works. No password should be sent to the agent or saved in scripts. Use your own authenticated terminal/password prompt. All commands below before section4 are source/files/read-only or file-only build, not hardware maintenance.

## 1. Windows: create NEW staging and transfer five pinned files

Run in your own PowerShell. Strict host-key checking stays enabled. If host key is unknown/changed, verify its fingerprint through your trusted Jetson console first; do not disable checking.

```powershell
$P = 'D:\for_cat\PHASE5_JETSON_HARDWARE_20261030'
$C = 'D:\for_cat\CANDIDATE_R2_OFFLINE_HARDENING_20261030'
$S = '/home/toan/phase5_for_cat_20261030_owner01'
ssh -o StrictHostKeyChecking=yes toan@192.168.123.8 "umask 077; test -d /home/toan && mkdir -m 700 '$S'"
if ($LASTEXITCODE -ne 0) { throw 'STOP: auth/path/existing staging; do not overwrite or retry blindly' }
scp -o StrictHostKeyChecking=yes "$C\R2_HARDENING_SOURCE.zip" "$C\tools\safe_release.py" "$P\owner_arm64.py" "$P\jetson_preflight.sh" "$P\http_readonly_audit.py" "$P\HANDOFF_SHA256SUMS" "toan@192.168.123.8:$S/"
if ($LASTEXITCODE -ne 0) { throw 'STOP: preserve partial staging and transfer error' }
ssh -o StrictHostKeyChecking=yes toan@192.168.123.8
```

If `owner01` already exists, review/preserve it and select a NEW suffix consistently; do not delete/overlay an old output. This session has not created any remote staging. Source remains separate from `/home/toan/for_cat`, R1 and R2.

## 2. Jetson authenticated terminal: checksums, read-only preflight, PLAN

```bash
S=/home/toan/phase5_for_cat_20261030_owner01
test -d "$S" && cd -- "$S"
sha256sum -c HANDOFF_SHA256SUMS
```

Stop if any checksum is missing/mismatched. Independent trusted anchors from Windows:

```text
ZIP       1c3b8abaf2586d91ac468c8c632d8750bf28a72d92f91130b983cb51dd99990d
verifier  5338e1200423241177cb52680ca225ef499eaa8fdc622c59250394a433a0d5f6
manifest  a92fc2586daacaabb5e931f0b8603bb1a3bd159a1cd747f43fd8b0cff0a968d4
```

After checksum PASS, run the metadata collector and inspect its per-command exits:

```bash
( set -C; sh "$S/jetson_preflight.sh" > "$S/owner_preflight.log" 2>&1 )
PRE_RC=$?
printf 'PREFLIGHT_SCRIPT_EXIT=%s\n' "$PRE_RC"
cat "$S/owner_preflight.log"
date -u
timedatectl status
python3 -B "$S/owner_arm64.py"
```

Preflight script overall0 is not a blanket PASS; see actual `EXIT_CODE=` entries, current unit PIDs/fuser, RAM/disk, R1 result and image hash. Time appears about+7h between API server and client; inspect, do not change time/services automatically. If services/USB/resources/compiler are not as expected, send logs and stop before build.

## 3. Only with satisfactory preflight: file-only ARM64 build once

```bash
python3 -B "$S/owner_arm64.py" --execute BUILD_AND_FILE_REPLAY_ONLY
RC=$?
printf 'OWNER_ARM64_EXIT_CODE=%s\nSTAGING=%s\n' "$RC" "$S"
```

The wrapper verifies ZIP/verifier, captures preflight, refuses low resources/another compiler, strictly validates/extracts a NEW `source/`, runs the **sealed native PLAN** then unchanged sealed execute helper. No Serial/camera/live Bridge/services/production DB operation is issued. Resource cap failures remain failures; do not lower guards/stop production just to force PASS.

Outputs:

- `$S/owner_run_<UTC>/result.json` and per-command `.log` files: timestamps, commands, exit codes, resources/transfer hashes, production identity before/after.
- `$S/source/hardening_arm64_owner_run_<UTC>/result.json`: actual compiler/dependencies, tests, source before/after and binary SHA256s.
- Same native directory: `bridge_compile.log`, test compile/test logs, `bridge_default_plan.log`, `dog_warning_rejected.log`.

Send both result files, `owner_preflight.log`, failing-stage log if any, and the printed exit code. Preserve failed outputs; do not rerun into the same source/output, disable Werror or import old binaries. A new retry should follow diagnosis, not a loop.

Optional GET-only capture **after the above review**, no auth spoofing:

```bash
python3 -B "$S/http_readonly_audit.py" --base http://127.0.0.1:8000
python3 -B "$S/http_readonly_audit.py" --base http://127.0.0.1:8000 --execute GET_EXISTING_STATUS --out "$S/http_owner_$(date -u +%Y%m%dT%H%M%SZ)"
```

401/403 means BLOCKED by access policy: use the existing legitimate browser/approved access path; do not forge forwarded identity headers.

## 4. Physical next step: provide evidence, not actuator commands yet

Current live error is **unsupported firmware mode** with zero valid frames; do not flash/restart/deploy to hide it. Review `SAFETY_GO_NO_GO.md`, then provide existing running-bank/security evidence, individual ECHO13/17/15/10 peak/protection data, actual wiring/supply/driver/isolation/cutoff details and HX RAM-loss acknowledgement. See `SENSOR_REAL_TEST.md`, `SERVO_TEST.md`, `PUMP_TEST.md` for scoped proposals.

A maintenance/Serial/reset/flash/servo/pump operation needs its own exact approval after prerequisites, command, risk, stop/handback and expected evidence are agreed. No food dispense authorized. **Aim35g/final30–40g inclusive; APP FLASH NO-GO; SERVO/PUMP LOCKED; MANUAL BUZZER DISABLED.**
