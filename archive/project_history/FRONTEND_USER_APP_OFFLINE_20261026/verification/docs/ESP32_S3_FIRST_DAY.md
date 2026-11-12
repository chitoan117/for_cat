# ESP32-S3 first-day gate — no peripherals or actuators

M3 bring-up pack now recommends the **identified CH343G bridge connector first** and `esp32s3_n16r8_hw_safe_uart`; the existing native-CDC target is a separate option, not the same port configuration. See `ESP32_S3_PC_DETECTION.md`, `ESP32_S3_FIRST_FLASH.md` and `M3_HARDWARE_BRINGUP_MASTER.md`. Candidate board/ports remain physically unverified.

1. Photograph both board sides and read the **exact seller board** markings/revision; keep photos with the evidence log.
2. Identify the exact ESP32-S3 module, not just the listing name; obtain matching module/carrier documents.
3. Confirm N16R8 marking; later read actual memory size. Our DevKitC-1 target is only a compile surrogate.
4. Identify which Type-C port(s) connect to a USB UART bridge versus native USB; inspect chip/connector labels/schematic.
5. Identify PCB/external antenna type and module variant; follow its RF antenna instructions before any later Wi-Fi use.
6. Do **not** connect sensors.
7. Do **not** connect servo.
8. Do **not** connect pump; use only verified board USB development power.
9. From project root on the PC, after confirming bridge routing: `& .\.tools-venv\Scripts\pio.exe run -d esp32 -e esp32s3_n16r8_hw_safe_uart`. Confirm serial/memory build matches the identified module; no blink/actuator/sensor GPIO enabled. Native connector uses the preserved native target only after separate review.
10. Detect port with `.\.venv\Scripts\python.exe -m serial.tools.list_ports -v` (Windows), or `ls -l /dev/ttyUSB* /dev/ttyACM*` on Linux; record actual node/COM and USB identifiers.
11. **Only after board/USB/memory review**, flash bridge HW_SAFE: `& .\.tools-venv\Scripts\pio.exe run -d esp32 -e esp32s3_n16r8_hw_safe_uart -t upload --upload-port COMx` (replace with actual port). Do not use the SIM image for physical validation.
12. Bridge-first image adds a once-only **monitor boot** metadata line, not v1 response fields; record it and ROM output, then close monitor. Preserved native profile has no required custom banner. Lack of a native-CDC banner is not proof of failure or success.
13. From `jetson/` on the PC with its venv, run `..\.venv\Scripts\python.exe -m tools.test_serial --device COMx --count 1`; require PING ACK with matching ID and CRC. (On Jetson use its actual detected device and interpreter.)
14. The same tool sends GET_STATUS; require SYSTEM_STATUS `01` and matching ID. This says protocol responsive, **not sensor/actuator health**. No feeding command is required.
15. Unplug, repeat low-rate check, reconnect and rediscover port, repeat; record OFFLINE/timeout then recovery. Stop on unexplained resets.
16. Record all actual outcomes in `HARDWARE_EVIDENCE_LOG_TEMPLATE.md`/a copied log and the Phase 2 validation record; builds alone do not clear the gate.
17. **Only then** complete `ESP32_S3_PIN_ASSIGNMENT_WORKSHEET.md` against the exact module/board. Do not wire anything until voltage/capability/reservation checks pass.

RC2 performs none of these physical steps automatically. No final GPIO or hardware success is claimed.
