# Pre-hardware baseline — historical pre-RC1 checkpoint

Historical navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

**HISTORICAL / NOT CURRENT:** the figures below record the pre-RC1 run. RC1 was its next checkpoint, not today's authority. Use `CURRENT_PROJECT_STATE.md` and `PRE_HARDWARE_FINAL_BASELINE.md` for the current handoff; older generic MCU/driver descriptions are superseded.

## Architecture and truth labels

USB webcam → Jetson Nano (Python/OpenCV, future AI, SQLite/REST) → USB serial → ESP32 (future sensor/actuator authority). Existing Web/App ↔ Jetson REST API; the frontend remains in its other project. **NO HARDWARE VERIFIED:** no Jetson Nano, Logitech webcam, ESP32 board, sensor, RTC, servo, pump or physical serial communication was available on this development PC.

| Label | Verified scope |
| --- | --- |
| SOFTWARE VERIFIED | Python 3.14.3 host suite: **88 passed, 0 failed** using `python -m pytest -q`; imports, model validation, persistence/restart, API and checks script. Python 3.10+ compatibility is source-level; no Jetson interpreter execution. |
| SIMULATION VERIFIED | Deterministic Python twin scenarios for feed acceptance/rejection/timeouts, restart, water hysteresis/failure, serial loss/recovery, temporal visits and end-to-end API/history. No device GPIO or physical pump/servo operation. |
| ESP32 COMPILE VERIFIED (PC) | Isolated PlatformIO Core 6.2.0; both `esp32dev_sim` and `esp32dev_hw_safe` succeeded targeting configured `esp32dev` + Arduino; **RAM 22,692 / 327,680 bytes (6.9%)**, **flash 284,104 / 1,310,720 bytes (21.7%)**, each. No compile errors; PlatformIO prints a Windows-terminal-codepage firmware-metrics notice but still prints RAM/flash. `esp32/test/native_safety.cpp` cross-compiles to an ESP32 object but has **not run** (no native host C++ compiler/MCU). |
| DATASET NOT AVAILABLE | `python -m ai.scripts.dataset_report` and `validate_dataset` report `DATASET_NOT_AVAILABLE`. No real images, labels, sessions or video were imported. Test images and predictions exist only in temporary SYNTHETIC_TEST_DATA fixtures. |
| AI NOT TRAINED | Interfaces/mocks, session-safe split, training-plan gate and pure-metric evaluator exist. No trained model, validated runtime, confidence/accuracy numbers or real predictions. |

## Modules / behavior

- Jetson: `app/config.py` validated `.env.example` defaults to MOCK, video/USB selection and fixed v1 115200 baud; `app/main.py` mounts FastAPI and explicit-origin CORS only. `app/api/routes.py` preserves Phase 1 routes plus feed result polling, typed sessions, food types, experimental preference evidence and UTC daily summary. SERIAL mode **never transmits FEED_REQUEST**. ACK means PENDING; loss after ACK does not invent SUCCESS. Feed requests use bounded rate, body and key checks; `Idempotency-Key` maps to a durable first-writer-wins ledger, including across a service restart. Ledger fills at 10,000 rows and fails closed rather than recycling IDs.
- `app/storage/event_store.py`: bounded in-memory/SQLite generic events; `storage/{records,repositories,summary}.py`: explicit SQLite `PRAGMA user_version=2` (0/1 migrate), bounded typed feeding/drinking/behavior/food/preference tables, UTC summary, and durable feed request ledger. Empty DB returns structured empty responses/null measurements. No raw sensor values or cat observations have been inserted.
- `app/serial_link/{protocol,real_transport,link_manager,mock_transport}.py`: frozen v1 CRC16/CCITT-FALSE binary frames; bounded byte-stream recovery and deterministic fuzz tests; correlated responses, timeout/reconnect and link stats. Real device transport is code only, NOT tested on USB hardware. Firmware still reports REJECTED for feeds and only protocol responsiveness for GET_STATUS; **water telemetry is absent from v1**.
- `app/camera/{mock_camera,usb_webcam,video_file}.py` plus `tools/replay_video.py`: optional bounded live/video capture, explicit EOF/reset and mock UNKNOWN predictions; no real USB webcam/video loaded. `app/behavior/{temporal,fusion}.py` uses monotonic time, ROI, confidence, confirmation and dropout to emit eating/drinking visits. Confirmed visits can be associated with a matching feeding session and stored; invalid/unsteady weights cannot yield a consumed-grams estimate, and drinking records contain no invented water volume. `app/analytics/preference.py`: documented **EXPERIMENTAL** multi-session behavioral trend with insufficient-data state, never emotion/certainty.
- ESP32 `platformio.ini`: default SIM, optional HW_SAFE and inert legacy alias; `include/{board_config,pins,safety_logic,sensor_drivers,safety_persistence}.h`: all physical pins `-1`, `ACTUATOR_OUTPUTS_ENABLED=0` compile-time guard, health-aware interfaces and deterministic feed/water policies. Daily record contains version/date/portions/grams/last feed/`needs_inspection`; portable policy locks on interrupted or invalid state. Portable C++ feed policy requires a successful NVS write-ahead `needs_inspection` before requesting servo open and persists counters before COMPLETE; a failed write faults. NVS durability/fault recovery/timing and **wiring real sensor/actuator drivers to that policy** remain unvalidated hardware work. MCU `src/main.cpp` remains inert; no motor/pump GPIO initialized and UART FEED_REQUEST still reports REJECTED.
- Simulator `jetson/app/simulator/` and `tools/run_simulator.py` accepts `scenarios.json`; cases include NORMAL, COOLDOWN_REJECTED, DAILY_LIMIT_REJECTED, FOOD_EMPTY, HX711_FAILURE, NO_WEIGHT_PROGRESS, FEED_TIMEOUT, RTC_INVALID, SERVO_FAILURE, WATER_NORMAL/LOW/FILL_SUCCESS/SENSOR_FAILURE, PUMP_NO_PROGRESS/TIMEOUT, SERIAL_DISCONNECT/RECOVERY and identity/behavior events. Python twin is separate from C++; no claim of on-device or native-C++ runtime execution.
- Dataset/AI `ai/dataset.py`, `ai/scripts/`, `ai/{training,evaluation}.py`, `datasets/schema.json`: opt-in dry-run imports, bounded extraction, resumable labeling, corrupt/exact/near-duplicate warnings, anonymous session IDs, session-safe deterministic splits, diversity report, per-class/FAR metrics from supplied predictions only. No training execution or automatic downloads.

## Frozen protocol and known limits

START `A5 5A`, VERSION 1, u32 LE request ID, u8 command, u16 LE length (max 256), CRC16 LE over VERSION..PAYLOAD. No incompatible wire change. ESP32 parser still needs real corrupted-frame/reconnect tests. PC framework build target is **not** proof of actual ESP32 board model. Hardware sensor drivers are unvalidated interfaces, not working pin drivers; no water telemetry over v1; C++ harness compile does not prove runtime safety. No Jetson Python/JetPack/OpenCV compatibility, USB frame FPS, ESP32 flash/NVS, electrical supply, network TLS/auth or model accuracy has been verified.

## Exact hardware gates remaining

1. Record real Jetson model/OS/JetPack/Python; run entire Python suite in compatible isolated environment.
2. Observe real Logitech USB webcam and bounded readable OpenCV frames with resolution/FPS/read failures.
3. Confirm exact ESP32 board, safe supply and unassigned GPIO policy; flash inert firmware with servo/pump disconnected; verify CRC, PING, GET_STATUS, disconnect/reconnect.
4. Calibrate/validate each sensor, RTC/NVS, power rails/level shifting and per-stage fault handling per `HARDWARE_TEST_PLAN.md`. Do not enable actuators without a separately reviewed firmware/output safety integration and physical tests.
5. Collect supervised real cat sessions only after consent/conditions and test dataset session leakage; train/evaluate AI only from such data. Frontend/network deployment also requires TLS/auth/CORS design in `OLD_FRONTEND_INTEGRATION.md`.

For commands, see `PHASE2_MANUAL_STEPS.md`; for software run `scripts/run_checks.ps1` on this PC (or `scripts/run_checks.sh` on a suitable Linux system). Earlier `PHASE1_BASELINE.md` / `PHASE2_HARDWARE_VALIDATION.md` contain dated historical baselines, not this checkpoint.
