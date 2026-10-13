# ESP32 build checklist (Phase 1.5 historical note plus current safe profiles)

At Phase 1.5, `pio --version` was unavailable. Subsequently PlatformIO Core 6.2.0 was installed in `.tools-venv` on the PC, and the inert `esp32dev_sim`/`esp32dev_hw_safe` profiles compiled. No device was identified, flashed, or runtime-tested. See `PRE_HARDWARE_BASELINE.md` for current build metrics.

1. Install PlatformIO in a suitable development environment and record `pio --version`.
2. Check `esp32/platformio.ini`: `espressif32`, `esp32dev`, Arduino framework, 115200 baud. Confirm the **actual** board model before selecting it for a device.
3. From `esp32/`, use the isolated `..\.tools-venv\Scripts\pio.exe run -e esp32dev_hw_safe` on Windows; record full compiler result and dependency versions. The default is `esp32dev_sim` and both profiles prohibit actuator outputs.
4. With actuators disconnected, confirm parser behavior on PING, GET_STATUS, FEED_REQUEST, FEED_STATUS, unknown commands, CRC errors, incorrect lengths, partial frames and request-ID correlation.
5. Verify FEED_REQUEST ACK is followed by FEED_STATUS REJECTED; ACK alone must never be counted as feeding success.
6. Before any future actuator enablement, validate durable request replay protection, sensor-fault interlocks, cooldown/daily limits, manual-button policy, actuators, supplies and timeout fail-safe on actual hardware. Current source contains only portable policy logic and a hard compile-time output guard.

No flash, webcam validation, pump activation or servo activation was performed. PC compilation is not hardware validation.
