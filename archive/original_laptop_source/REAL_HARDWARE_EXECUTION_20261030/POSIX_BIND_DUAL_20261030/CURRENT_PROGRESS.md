# Resume checkpoint — POSIX_BIND_DUAL_20261030

- Source-level bind is now INSIDE `bridge/esp32_bridge.cpp::bridge()`, not just standalone callbacks. Backend uses SQLite outbox, never a second Serial owner.
- Latest source/evidence: INTEGRATION_RESULT.md and RESULT.json / SOURCE_CHANGES.patch.
- PASS_OFFLINE:14 full-Bridge integration cases;8 actual dual firmware-loop cases; ESP32-S3 dual APP423712bytes/SHA01c056e0…e706232; local Linux/POSIX x86_64 object-only compile.
- Two original APP images415456/377840bytes remain byte-identical and were not rebuilt. Previous qualified suites retained, not rerun.
- New dual image supports manual commands plus binary negotiation; automatic feed remains disabled, closure provider false, pump INERT/buzzer disabled. No fake physical closure from PWM.
- Jetson/Linux linking/runtime, physical firmware/servo/E2E/REAL-ingest qualification still NOT_RUN/BLOCKED. No production/device action.
- Pump motor two-wire isolation already OWNER_CONFIRMED. Next owner evidence: servo model/power/GND/cutoff/safe mechanism before approved APP-only/manual test. APP FLASH NO-GO.
