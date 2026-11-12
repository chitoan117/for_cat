# Pre-hardware release candidate RC1 — host checkpoint

Historical navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL / NOT CURRENT:** counts, footprints, generic MCU references and driver gaps describe RC1. Current architecture/status: `REFERENCE_ARCHITECTURE.md` / `CURRENT_PROJECT_STATE.md`. Historical PC camera evidence is not Jetson/required-hardware validation.

## Architecture and environment

Webcam → Jetson Nano (Python/OpenCV, REST, local SQLite, future AI) → USB serial → ESP32 (local safety authority, future sensors/actuators). Existing Web/App ↔ Jetson API; no frontend work was done. Source commands use project-relative paths; Windows examples name `D:\forr_cat`, Jetson examples `$HOME/forr_cat`. The current execution workspace's physical directory name does not establish the eventual deployment path.

| Category | RC1 evidence / remaining gate |
| --- | --- |
| SOFTWARE VERIFIED | Windows Python **3.14.3**: `scripts/run_checks.ps1` completed **99 Python tests, 99 passed, 0 failed** (API integration, typed DB, simulator, dataset/AI tools, protocol fuzz and golden vectors). `scripts/setup_dev_windows.ps1` created isolated `.venv`/`.tools-venv`; top-level runtime/test packages and PlatformIO version are pinned. Jetson practical minimum remains Python 3.10+ pending device test. |
| HOST C++ LOGIC VERIFIED | Official portable Zig **0.16.0** compiled and **executed** `esp32/test/native_safety.cpp`: **101 assertions passed, 0 failed**, including safe boot, feed/water faults, limits, next-day counter reset, persistence, timeout and 7 UART vectors. The build disables a nullability diagnostic from Zig's bundled libc++ headers only; no project-code compiler warnings were suppressed. Assertions test portable logic, not ESP32 hardware. |
| SIMULATION VERIFIED | `jetson/app/simulator/scenarios.json` has **21 deterministic scenario definitions**; Python tests exercise feed results, water outcomes, owner/other/empty subject, behavior, serial loss/reconnect and durable request handling. Policy parity/deliberate differences: `SIMULATION_FIRMWARE_PARITY.md`. |
| PC BUILD VERIFIED | Isolated PlatformIO Core **6.2.0**, pinned `espressif32@55.3.311`, configured `esp32dev` Arduino target: `esp32dev_sim` **PASS**, `esp32dev_hw_safe` **PASS**. Both use **22,692 / 327,680 RAM bytes (6.9%)** and **284,076 / 1,310,720 flash bytes (21.7%)**. PlatformIO printed a Windows codepage firmware-metrics notice during compilation, though it reported RAM/flash; no compiler errors. No flash/upload occurred. |
| DATASET NOT AVAILABLE | `python -m ai.scripts.validate_dataset` reports `DATASET_NOT_AVAILABLE`; images in tests are clearly synthetic temporary fixtures, not collected cat data. |
| AI NOT TRAINED | Interfaces, empty-data handling, evaluation arithmetic tests and training-plan gate exist; no weights, cat dataset, validated model inference or real-world metrics. |
| NOT JETSON VERIFIED | Jetson model/OS/JetPack/Python environment, install scripts, USB webcam, Jetson OpenCV/FPS and local REST behavior still need physical testing. |
| NOT ESP32 HARDWARE VERIFIED | Actual board model, flashing, USB serial, CRC replies, reconnect and NVS power-loss durability have not been tested on an ESP32. |
| NOT SENSOR VERIFIED | HX711, level sensors, RTC, OLED, buzzer, button, pin map and electrical levels are unvalidated. UART v1 has no real water telemetry. |
| NOT ACTUATOR VERIFIED | Servo and pump must stay disconnected; `ACTUATOR_OUTPUTS_ENABLED=0` fails compilation if changed, all GPIOs remain unassigned and firmware still ACKs then rejects FEED_REQUEST. |

**PC WEBCAM VERIFIED (not a Jetson/Logitech result):** `python -m tools.test_webcam --camera-index 0 --seconds 3` on this Windows PC read **83 frames**, **640×480**, **approximately 27.35 FPS** over **3.03 s**, **0 read failures**, and saved one temporary inspection frame. Windows PnP lists **HP Wide Vision HD Camera**; camera-index-to-model association was not independently established and no Logitech camera was identified. This is not dataset capture and does not clear the Jetson/Logitech gate.

## Protocol, API and persistence

UART v1 is unchanged: `docs/UART_V1_GOLDEN_VECTORS.csv` is the single canonical byte set for PING, GET_STATUS, FEED_REQUEST, ACK, NACK, FEED_STATUS and SYSTEM_STATUS. The Python encoder and portable C++ encoder used by firmware both match all seven vectors. `ACK != SUCCESS`. The compatible REST `/api/v1` snapshot is `API_V1_CONTRACT.md`; existing Web/App integration design is `OLD_FRONTEND_INTEGRATION.md`. SQLite typed schema is version 2, bounded generic events and a fail-closed durable feed-request ledger; maintenance commands are in `DATABASE_MAINTENANCE.md`.

## Known limitations and next gates

- Portable safety policies are host-tested, but actual `main.cpp` intentionally never drives any actuator; physical sensor drivers, exact board pins and RTC/NVS timing remain unimplemented/unvalidated. The Python twin uses synthetic healthy inputs; its SUCCESS is not current firmware's physical outcome.
- The release has no Jetson-installed runtime validation and no actual Logitech webcam or ESP32 USB link. `scripts/setup_jetson.sh` and `check_jetson_env.sh` are prepared but **not run on Jetson**. Real-camera PC evidence cannot substitute for Jetson OpenCV validation.
- No cat dataset exists. Dataset collection, food experiment and daily report expectations are specified in `DATA_COLLECTION_PROTOCOL.md`, `FOOD_PREFERENCE_EXPERIMENT.md` and `BEHAVIOR_REPORT_CONTRACT.md`. Preference trend is experimental and requires multiple reliable sessions.
- No public API security deployment is in place: authentication/TLS, Web/App browser HTTPS/local-network restrictions and production CORS require later design. Keep the default local bind and avoid exposing the Jetson publicly.

**RC1 freeze scope:** software/host logic and safe PC build can be frozen. The Phase 2 physical completion gate remains open: real Jetson environment/tests, Logitech → Jetson readable frames, and Jetson → USB serial → actual ESP32 correlated response with servo/pump disconnected. Follow `PHASE2_MANUAL_STEPS.md`; do not mark hardware or AI validated from this RC1.
