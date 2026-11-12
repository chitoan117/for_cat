# Pre-hardware RC2 — consolidated host evidence

Historical navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL / NOT CURRENT:** RC2 counts/footprints/implementation scope below are retained, not current handoff claims. Read `CURRENT_PROJECT_STATE.md` / `PRE_HARDWARE_FINAL_BASELINE.md` first; canonical architecture is `REFERENCE_ARCHITECTURE.md`.

## Starting condition and scope

Milestone remains **M2**. `RC2_STARTING_POINT.md` records the unchanged initial run: RC1 99 Python tests, 101 native C++ assertions, 7 UART vectors, classic SIM/HW_SAFE builds PASS. `PRE_HARDWARE_RC1.md` and `API_V1_CONTRACT.md` are preserved. No Git repository exists in this workspace; no reset/commit/push performed.

Architecture at the HISTORICAL RC2 checkpoint: normal USB webcam → Jetson Nano (OpenCV, injected future AI, temporal tracking, fusion, SQLite/REST) → USB serial → generic ESP32 / then-candidate ESP32-S3 N16R8 → future sensors/actuators; existing Flutter Web/App ↔ Jetson API. No frontend changed, no AI camera, no physical GPIO operation, no model training or external dataset download. **NOT CURRENT target selection:** today's sole target is the ESP32-S3 candidate in `REFERENCE_ARCHITECTURE.md`; classic profiles are regression targets only.

## Final checks (actual Windows PC run)

`scripts/run_checks.ps1` completed after source changes, using isolated Python **3.14.3**, PlatformIO Core **6.2.0**, Arduino **3.3.11**, ESP32 platform **55.3.311**, Xtensa toolchain **14.2.0+20260121**, and native Zig **0.16.0**. Optional host OpenCV **4.13.0.92** and NumPy **2.5.3** were installed only in `.venv` for generated-video tests; no ML frameworks were installed.

| Label | Exact result |
| --- | --- |
| SOFTWARE VERIFIED | **125 Python tests: 125 passed, 0 failed, 0 skipped**, including all 99 RC1 tests, API, SQLite reopen, idempotency, loss/stale responses, orchestration, preference/fusion and dataset/video tests. |
| HOST C++ LOGIC VERIFIED | **140 native assertions: 140 passed, 0 failed** (all 101 RC1 checks retained), dispatcher/record codec/health changes included. Plus **5/5** compile guards: valid default compiles; actuator-enabled, conflicting board, invalid USB and SIM/HW_SAFE mixed execution cases fail closed as expected. |
| SOFTWARE VERIFIED | **7/7 UART v1 golden vectors** remain byte-identical in Python and the C++ encoder used by firmware; the CSV was not changed. Seeded UART/REST/metadata fuzz tests pass. |
| SIMULATION VERIFIED | All **21 existing scenario definitions** remain covered in passing tests. New offline synthetic-model tests verify eating/drinking sessions, OTHER_CAT/UNKNOWN no automatic action, dropout, EOF, model failure, typed history and restart. No animal was recognized. |
| HOST VIDEO CODEC VERIFIED | A temporary **12-frame 64×48 10 FPS MJPG AVI** was locally encoded and decoded through OpenCV/VideoFileCameraProvider; frame order, presentation-time intervals and EOF verified. No webcam opened. |
| SOFTWARE VERIFIED | Temporary dataset round-trip: **3 synthetic videos × 3 extracted frames**, then a separate SKIP/UNUSABLE still; import/metadata/labels/report/session-safe split/duplicate/corrupt checks pass. Temporary directories removed; fixture never entered `ai/datasets/`. |
| DATASET NOT AVAILABLE | Real `ai/datasets` validation still reports `DATASET_NOT_AVAILABLE`; no real cat images/labels/splits. |
| AI NOT TRAINED | Default models remain UNKNOWN/no invented confidence; no trained weights, inference runtime, real accuracy or food-preference study. |

## Four firmware builds

All profiles keep `ACTUATOR_OUTPUTS_ENABLED=0`, all application pins unassigned and no raw GPIO operation. No firmware was flashed or run on a physical MCU.

| Profile | Classification | Final build | RAM (internal budget 327,680 B) | Flash (application slot budget) |
| --- | --- | --- | --- | --- |
| `esp32dev_sim` | PC BUILD VERIFIED | PASS | **22,860 B (7.0%)** | **285,380 / 1,310,720 B (21.8%)** |
| `esp32dev_hw_safe` | PC BUILD VERIFIED | PASS | **22,796 B (7.0%)** | **286,120 / 1,310,720 B (21.8%)** |
| `esp32s3_n16r8_sim` | ESP32-S3 COMPILE SURROGATE VERIFIED | PASS | **23,544 B (7.2%)** | **319,404 / 6,553,600 B (4.9%)** |
| `esp32s3_n16r8_hw_safe` | ESP32-S3 COMPILE SURROGATE VERIFIED | PASS | **23,480 B (7.2%)** | **320,128 / 6,553,600 B (4.9%)** |

The first S3 HW_SAFE attempt exposed a macro/enum-name collision, which was fixed with the distinct `FORR_HW_SAFE` macro. Final builds have no compiler errors. PlatformIO still printed its Windows codepage firmware-metrics notice while linking; RAM/flash reports were nevertheless printed, not guessed. The native runner retains RC1's narrow suppression of a Zig libc++ nullability diagnostic; no failing assertion or project defect was suppressed.

### N16R8 configuration status

Official `esp32-s3-devkitc-1` is the chosen **COMPILE SURROGATE ONLY**. Its base manifest is N8/no PSRAM; inspected Arduino menus/package libraries support overrides: `board_upload.flash_size=16MB`, package `default_16MB.csv`, `board_build.arduino.memory_type=qio_opi`, `board_build.psram_type=opi`, `BOARD_HAS_PSRAM`. The resulting S3 link map includes `qio_opi` libraries/PSRAM init and image build selects **16MB**. Each OTA app slot is 0x640000; application percentages are relative to that slot, not the whole flash.

This verifies **memory compile configuration**, not physical capacities. Actual **8 MB PSRAM detection, 16 MB flash detection**, memory voltage/mode, module markings, external antenna, Type-C routing and all 44-pin seller GPIOs remain **NOT EXACT SELLER BOARD VERIFIED / NOT HARDWARE VERIFIED**. No fictitious PSRAM-capacity define was added. Confirm exact board before flashing. See `ESP32_S3_USB_SERIAL_OPTIONS.md` and the pin worksheet.

## Implementation and safety semantics

- Board layer distinguishes `CLASSIC_ESP32DEV` and `GENERIC_ESP32_S3_N16R8`; every application pin remains `PIN_NOT_ASSIGNED`. Guards fail on invalid board/USB/actuator configuration. No production pin table exists. `serial_port.h` selects bridge UART0 or native S3 HW CDC; ports remain configured by the host. Four compiled profiles cover classic UART0 and S3 native serial; a seller bridge requires a reviewed safe configuration after identification.
- `command_dispatch.h` is used after the firmware frame validator. SIM request → ACK → portable feeding policy with synthetic 10 g target/time/weights → PENDING → correlated FEED_STATUS. Completion requires policy target/closing/persistence, never ACK alone. HW_SAFE accepts the frame but returns REJECTED, with local `SAFE_BUILD_ACTUATORS_DISABLED` reason. V1 carries only one result byte; no incompatible grams/text reason/water payload added.
- MCU dispatch replay is bounded to 16 retained IDs, full ledger fails closed; duplicates are ACKed/queried without another simulated portion. Reboot does not resume feeding. SIM uses memory counters, not real NVS. HW_SAFE compiles `Preferences` storage but never executes a physical feed.
- Safety record storage is now a fixed 25-byte **v3 envelope** with CRC, explicit encoding/no compiler padding. Counter record revision is still 2. Missing/old/corrupt state fails closed; nothing resets safety counters automatically. Same-day/date/grams/last-feed restore and corruption are host-tested. Write-ahead inspection flag remains required before desired-open, completion counters persist before success. **NOT NVS HARDWARE VERIFIED**.
- `ObservationPipeline` injects camera, identity/behavior models, tracker and optional future fusion context. It supports one-shot and bounded synchronous execution, pacing/cancellation, failure/EOF and structured logging. FastAPI constructs it but does not start an unattended camera loop. Models default UNKNOWN, confidence absent, status MOCK; unvalidated injections never become AI READY. No identity-triggered automatic feeding policy exists.
- Typed visits are canonical. Atomic exact retries are idempotent; conflicts never overwrite. Existing Event-shaped history endpoints use read projections, not duplicate writes. Confirmed drinking/eating appear in API history and UTC summary. A camera eating visit is distinct from a dispensed FeedingSession. EOF ends at the last positively observed frame, with explicit completion_reason; model errors/dropout never invent duration.
- Stable/validated pre/post weights and a confirmed matching eating visit may yield consumed grams; unstable, faulty, increased weight, missing post or known food addition yields null. By default orchestration has no measurements. Experimental multi-food tests exercise minimum sessions, weights, mean eating duration (evidence only), leftovers and consistency using **SYNTHETIC_TEST_DATA**.
- SQLite pending/completed ledger reopen tests and duplicate client/serial results pass. Link loss after ACK stays PENDING; a retry uses the original request ID, not another command. A stale result cannot resolve it. If the device disappears during a result poll after heartbeat, `esp32_online=false`/link OFFLINE. GET feed result reads retained state; `/status` refreshes from transport. All physical feed requests remain blocked in SERIAL API mode.
- Original API v1 paths/FeedResult/Event shapes and UART v1 bytes preserved. AI status is additive; observation projections add EATING/DRINKING evidence to generic history without claiming a dispensing action. Frozen RC1 contract file is untouched; `RC2_ORCHESTRATION_AND_HISTORY.md` documents these compatible additions. No `/servo`, `/pump` or `/gpio` endpoint is exposed.

## Files created

- `docs/RC2_STARTING_POINT.md`
- `docs/ESP32_S3_PIN_ASSIGNMENT_WORKSHEET.md`
- `docs/ESP32_S3_USB_SERIAL_OPTIONS.md`
- `docs/ESP32_S3_FIRST_DAY.md`
- `docs/HARDWARE_EVIDENCE_LOG_TEMPLATE.md`
- `docs/ROBOFLOW_WORKFLOW.md`
- `docs/JETSON_INFERENCE_INTEGRATION_PLAN.md`
- `docs/REFERENCE_ARCHITECTURE.md`
- `docs/REFERENCE_MAP.md`
- `docs/RC2_ORCHESTRATION_AND_HISTORY.md`
- `docs/PRE_HARDWARE_RC2.md`
- `esp32/include/command_dispatch.h`
- `esp32/include/serial_port.h`
- `esp32/include/safety_record_codec.h`
- `jetson/app/ai/pipeline.py`
- `jetson/app/storage/history.py`
- `jetson/tools/run_observations.py`
- `jetson/tests/test_observation_pipeline.py`
- `jetson/tests/test_rc2_evidence.py`
- `ai/tests/test_video_roundtrip.py`
- `scripts/test_safe_build_guards.py`

## Files modified

- `esp32/platformio.ini`, `esp32/src/main.cpp`, `esp32/test/native_safety.cpp`
- `esp32/include/board_config.h`, `pins.h`, `safety_logic.h`, `safety_persistence.h`
- `jetson/app/main.py`, `jetson/app/api/routes.py`
- `jetson/app/behavior/models.py`, `fusion.py`, `temporal.py`
- `jetson/app/storage/records.py`, `repositories.py`, `summary.py`
- `jetson/app/camera/video_file.py`, `jetson/app/simulator/controller.py`, `jetson/app/analytics/preference.py`
- `scripts/run_checks.ps1`, `scripts/run_checks.sh`
- `README.md`, `docs/PROJECT_STATUS_CURRENT.md`, `docs/POWER_AND_ELECTRICAL_SAFETY.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/UART_PROTOCOL.md`, `docs/HARDWARE.md`, `docs/SIMULATION_FIRMWARE_PARITY.md`, `docs/SIMULATION_AND_AI_TOOLING.md`

Ignored `.venv`, `.pio`, native executables and test temporary files are generated host artifacts, not source or hardware evidence. No old Flutter project, UART CSV, RC1 report or API v1 snapshot was replaced.

## Unverified items / real-arrival gates

**NOT JETSON VERIFIED:** exact Nano model/JetPack/Python compatibility and OpenCV/model performance; prepared setup scripts are not an on-device pass. **NOT ESP32 HARDWARE VERIFIED:** seller board/USB, flash/upload, UART link/reconnect and NVS power-loss behavior. **NOT GPIO VERIFIED / NOT SENSOR VERIFIED / NOT ACTUATOR VERIFIED:** pins, voltage/level shifting, power, load cell/RTC/ultrasonic and real PWM/pump drivers/mechanics remain blocked. **DATASET NOT AVAILABLE / AI NOT TRAINED:** generated fixtures are not cat data, no inference accuracy or preference certainty claimed. Network auth/TLS and old frontend integration remain untested.

When S3 arrives: follow `ESP32_S3_FIRST_DAY.md`—photograph/read module and N16R8 marking → identify USB/antenna/memory → sensors/servo/pump DISCONNECTED → review safe compile config → detect actual COM/node → flash HW_SAFE only → record available boot output, PING/GET_STATUS/CRC/IDs and unplug/replug → evidence log → only then finalise verified GPIO capabilities. Never flash based only on a seller title.

When Jetson arrives: from `$HOME/forr_cat`, `sh scripts/check_jetson_env.sh`; record OS/JetPack/Python. If the interpreter is compatible (3.10+), explicitly run `sh scripts/setup_jetson.sh`, then its isolated tests, discover real Logitech node and run bounded webcam test; connect identified safe ESP32 via USB, discover serial node, test PING/GET_STATUS/recovery. Unsupported Python must be addressed in isolation, not by replacing JetPack/system Python. Full manual commands remain in `PHASE2_MANUAL_STEPS.md`.

**Freeze decision:** PRE-HARDWARE RC2 may be frozen for software, host logic, generated-video and surrogate compilation evidence. It does not clear M3 or any physical/data/AI-training gate. No further hardware-dependent action starts automatically.
