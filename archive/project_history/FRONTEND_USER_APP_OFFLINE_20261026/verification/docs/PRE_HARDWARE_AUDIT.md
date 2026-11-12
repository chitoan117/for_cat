# Pre-hardware audit — initial repository state

Historical navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL / NOT CURRENT:** initial state before later implementations. Missing-feature/driver claims and test counts below are not current. See `CURRENT_PROJECT_STATE.md` and `REFERENCE_ARCHITECTURE.md`.

## Current architecture
USB webcam → Jetson Nano (Python/OpenCV, future AI, bounded SQLite, REST) → USB serial → ESP32 (local safety authority, sensors and eventual actuators). Existing Web/App ↔ Jetson REST; frontend is separate. No real device or dataset available on this PC.

## Inspected modules / status at start of this session
- `jetson/app/main.py`, `api/routes.py`: health/status/events/manual feed and reserved behavior/history paths. SERIAL mode blocks feed requests; mock mode can complete in tests. `/status` polls pending operations. No authentication, rate limits, client idempotency, or background polling.
- `jetson/app/camera/{base,mock_camera,usb_webcam}.py`: camera abstraction, synthetic frame and optional OpenCV capture. No video replay or temporal pipeline.
- `jetson/app/serial_link/{protocol,transport,real_transport,mock_transport}.py`: v1 framed codec with CRC and correlated replies; real transport retries opening after loss. Python decoder only accepts whole frames and cannot resynchronize byte streams by itself; transport does limited START scanning. No link manager/statistics.
- `jetson/app/storage/event_store.py`: bounded in-memory and SQLite generic event stores; no typed session repositories or explicit schema version.
- `jetson/app/{ai,behavior}/models.py`: enum contracts, observation placeholders; no inference, food-preference analysis or fusion. `ai/` contains only empty placeholders; no data, dataset tooling, models or evaluation.
- `esp32/src/main.cpp`, `include/hardware_interfaces.h`: inert incremental parser; PING/status and ACK feed then report REJECTED. 16-ID replay cache volatile; no drivers, safety controller, water state machine, NVS or validated pins. `platformio.ini` originally selected only `esp32dev` Arduino. Firmware communicates via USB serial but never operates hardware.
- `jetson/tests/`: 38 host tests passed before this work; camera and serial hardware not tested. `jetson/tools/`: bounded webcam and serial manual utilities.
- Documentation in `docs/` describes the same architecture; `PHASE1_BASELINE.md` is historical (Python 3.11 before compatibility update), `PHASE2_*` records hardware as unverified. `UART_PROTOCOL.md` still calls the real transport reserved; update current descriptions without rewriting historical records.

## Duplicate/dead code and critical gaps
No duplicated frontend or MCU architecture. `SafetyController::mayFeed` in `esp32/include/hardware_interfaces.h` is an inert placeholder, not an implemented safety policy. The mock transport represents explicit test outcomes, not the firmware controller. API feed states and event-store histories exist in different representations; neither is a complete persisted transaction/session model. Protocol v1 is matched across Python/C++ but needs streaming fuzz/recovery tests; no wire-format change is justified. The highest risks are accidental actuation, counter loss across restart, idempotency after feed-cache eviction, trusting unvalidated sensor/RTC data, serial reply loss after ACK, stale replies, unbounded in-process feed state, insufficient security for LAN/public exposure, dataset session leakage, and inaccurate inference from isolated frames.

## Hardware/data/network boundaries
Real pinout, Jetson runtime, camera frame rate, ESP32 flash/serial operation, HX711/ultrasonic/RTC, electrical supply and NVS durability all require hardware validation. Cat identity/behavior evaluation and preference trends require labeled real sessions, calibration and bias assessment. No public HTTPS endpoint, auth, TLS termination, or production CORS policy exists; a Cloudflare-hosted HTTPS browser cannot safely assume access to a private HTTP Jetson API. No numeric hardware or AI performance claim follows from simulation.
