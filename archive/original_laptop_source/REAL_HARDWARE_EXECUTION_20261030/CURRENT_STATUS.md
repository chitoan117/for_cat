# Real hardware execution — STEP 1, waiting for owner terminal output

> **Continuation 2026-10-30:** STEP1 source/PID information is now OWNER_CONFIRMED. Integrated candidate has been built; latest handoff is `INTEGRATED_MANUAL_CANDIDATE/HANDOFF.md` and `RELEASE_RECEIPT.json`. Selected APP415456bytes/SHA77faf097…aecaac93; servo small-bench firmware ready, pump remains polarity-gated INERT. This earlier STEP1 record is preserved below; do not repeat its owner command or ARM64/AI/service qualifications.

Date: 2026-10-30. Priority: servo → pump → buzzer → sensors → gated integration. No ARM64 build, AI training, UNO or unrelated Windows tests.

## New owner statements accepted

OWNER_CONFIRMED: owner at device; assembly complete; authenticated Jetson SSH; Phase5 source transfer SHA PASS; GCC7.5 and three services verified; AI CAT/DOG functioning smoothly. Do not repeat these qualifications merely to refresh PASS. They do not by themselves identify the currently flashed app or prove power/polarity/servo endpoints.

## Source mapping checked locally

Authoritative inspected tree: `D:\for_cat\HARDWARE_PHYSICAL_BRINGUP_20261029\firmware`.

| Signal | Source evidence | Result |
|---|---|---|
| Servo GPIO6 | `include/current_hardware.h:9`; `include/m4/ledc_servo.h:44` static_assert; `src/servo_bench.cpp:43` | VERIFIED_PASS source mapping; matches USER |
| Pump GPIO7 | `include/current_hardware.h:9`; `src/pump_bench.cpp:12` static_assert | VERIFIED_PASS source mapping; matches USER; F5305S polarity NOT_VERIFIED |
| Buzzer GPIO2 | `include/current_hardware.h:7`; `include/m4/approach_dog_warning.h:8–10`; diagnostic banner | VERIFIED_PASS source mapping; ACTIVE_LOW3V3 in this profile, actual wiring/voltage not measured in this session |

`include/pins.h` assigns generic safe actuator pins -1 by design; it does not select another physical pin. Sensor profile explicitly disables actuator drivers. No contradictory GPIO6/7 assignment found in reviewed local bench code. Remote source comparison remains pending. User's CLOSED=white gate covering outlet / OPEN=gate rotated away is retained; no provided mechanical observation yields numeric endpoints yet. No angle guessed or sweep requested.

## Firmware command capabilities from actual local source

| Profile | Commands / capability |
|---|---|
| HX711_REFERENCE | `status`, `help`, `load`, reference/calibration/tare-related commands; **no servo/pump/buzzer controls**. Static asserts keep actuators disabled. Do not issue any calibration-changing command. |
| diag_four_ultrasonic | Sensor-only; `DisabledServo` / `DisabledPump` in `src/diagnostics.cpp:42–43`; sensor-image flags disable actuator diagnostics. Not an actuator bench image. |
| diag_servo_bench | `servo status`; `servo configure MIN_US MAX_US CLOSE_US OPEN_US CONFIRM`; `servo arm YES`; `servo open`; `servo set PULSE_US`; `servo close/disarm/stop`. Separate isolated image. ARM can move to CLOSE immediately. Safe parameters and exact running capability must be known before authorization. |
| diag_pump_bench | `pump status/arm YES/on MS/off/disarm`; shipped profile PHYSICAL_ENABLE0/OFF_LEVEL-1 is **INERT**, rejects ARM/ON. Active variants require measured OFF polarity and separate conditional image. |
| diag_dog_buzzer | `status`; `buzzer-driver ACTIVE_LOW CONFIRM`; `test CONFIRM`; `stop`; two200ms beeps/gap200ms,60s cooldown/max3tests per boot. Separate manual image; does not enable production DOG rule. |

Having these source files does **not** prove the loaded firmware implements these commands. The already prepared isolated servo APP is the minimal existing route if the current image lacks servo support; do not merge/unlock all actuators or flash it automatically. APP-only flash still needs actual bank/security/recovery and separate approval; RAM calibration preservation is not guaranteed by preserving NVS.

## Actual device/API observation this turn

Executed local command: `.venv\Scripts\python.exe -B REAL_HARDWARE_EXECUTION_20261030\read_existing_state.py`, exit **0**. Two existing GET-only endpoints, no Serial/control requests.

Evidence: `read_20261030T031137Z/{esp32_status.json,bridge_events.json,receipt.json}`. Receipt contains client UTC, full GET commands, HTTP status, exit and SHA256 per response.

- `/api/v1/esp32/status`: HTTP200; `/dev/ttyACM0`, USB serial5C85066678, `serial_connected=true`, **serial_tx_enabled=false**, `actuator_execution=false`.
- **ESP32_BAD_TELEMETRY; valid_reports0; telemetry=null; telemetry_usable_now=false**; parse_errors9889/noise9893/oversized0.
- `/api/v1/esp32/events?limit=5`: HTTP200; latest seq43001/server10:11:13Z still **unsupported firmware mode**.
- Fresh observations confirm current Bridge rejects incoming firmware mode and exposes no enabled serial TX path. They do not reveal the exact unsupported mode string/running partition. Known HX reference source emits HX711_REFERENCE rather than expected diag_current_hardware; this explains the known mismatch if that app is running, but current runtime identity is not yet proven.
- Prior agent SSH auth failed; no new repeated authentication attempt. Owner's authenticated terminal is the immediate valid path. No current command was run by agent in a Jetson shell in this turn.

## Physical results — do not fabricate

- SERVO_CLOSED_ANGLE / SERVO_OPEN_ANGLE: **NOT_MEASURED**. Bench uses pulse_us; an angle conversion also needs a justified servo mapping. OPEN→CLOSED real test NOT_RUN.
- Pump ON/OFF/real water flow: **NOT_RUN**. Polarity/power/priming/first activation authorization pending.
- Buzzer sound: **NOT_RUN**; production rule still DISABLED.
- Sensors: **BLOCKED_FIRMWARE on current accepted telemetry path**, not diagnosed broken. HX711 static PASS preserved, no tare/calibration write. Four ECHO peak/protection gates precede triggering.
- CAT/DOG/NONE actuation integration: NOT_RUN. No per-frame feed requests, DOG feed, automatic food cycle or rule deployment enabled. Aim35g/final30–40g inclusive retained for separately approved closed-loop trial.

## ONE next step

Owner pastes `NEXT_OWNER_COMMAND.sh` block in already authenticated Jetson terminal and returns output. It reads only selected source lines, Bridge launch metadata and12 existing journal lines; does not open tty, stop service, reset/flash, move a servo or alter calibration.

Expected evidence: actual remote source pin/profile/command excerpts and active Bridge command line; journal may identify firmware mismatch more precisely. Missing files/errors stay evidence, not a reason to scan the whole repository. Source excerpts still do not certify the flashed app.

After that output, select the shortest valid route to the **first supervised servo step**, asking only the outstanding power/GND/cutoff/firmware/parameters and specific activation approval. If identification needs exclusive Serial or a new image, stop first for scoped maintenance/flash approval. Demo before04/11/2026 remains the goal, not authority to bypass those conditions.

**No Serial opened, service stopped/restarted, flash/reset or actuator command issued. APP FLASH NO-GO; SERVO/PUMP activation pending specific approval; manual production buzzer DISABLED.**
