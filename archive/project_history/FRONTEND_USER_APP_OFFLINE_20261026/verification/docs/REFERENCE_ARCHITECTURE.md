# Reference architecture — CURRENT, M2 handoff

```text
NORMAL USB Webcam
    ↓
Jetson Nano
    Camera/OpenCV → injected identity/behavior model boundary
    → temporal sessions → session fusion → SQLite → REST API
    ↓ USB serial (UART v1 binary frames)
ESP32-S3 measured chip/16MB flash; PSRAM NOT DETECTED (no-PSRAM profile)
    configured sensor/UI driver and diagnostic foundations (host/compile verified only)
    local feed/water safety → separate safety/calibration persistence
    RTC DS1302: CLK16 / bidirectional DAT17 / CE18 (not I2C)
    OLED I2C: SDA8 / SCL9
    servo/pump interfaces: physical outputs hard-disabled

Existing Flutter Web/App ↔ Jetson REST API
```

**NO STM32. NO ESP32-CAM. NO AI CAMERA REQUIRED.** A normal USB webcam supplies pixels; future trained AI runs on Jetson, not on the webcam or ESP32. No frontend recreated or modified.

This is the single current architecture. Classic and N16R8 profiles remain legacy regression/surrogate only, not a second production architecture or this physical board. User reports actual S3revv0.2/40MHz/16MB flash, PSRAM NOT DETECTED, bridge1a86:55d3/cdc_acm,/dev/ttyACM0. GPIO4..13 sensor test-target mapping is candidate, final GPIO/voltage verification pending; actuator14/15 remain unassigned/disabled. Normal USB serial is the current link, no GPIO-UART/Wi-Fi control change.

Current physical facts/provenance: `M3_PHYSICAL_VALIDATION_RECORD.md`; current state: `CURRENT_PROJECT_STATE.md`; safe manual continuation: `REAL_HARDWARE_NEXT_STEPS.md`. Existing host pre-hardware evidence is historical, not rewritten as physical results. User-reported720pMJPG webcam29.97FPS/300frames/0fail and initial PING/GET_STATUS/CRC/IDs PASS exist; post-reconnect protocol remains user-reported without raw receipt. Formal closeout pending, no M4 PASS. Nano system Python3.6 is preserved; modern API is blocked until isolated runtime solution. AI shadow true, no owner dataset/trained model/client deployment/physical feeding.

RTC hardware changed from planned DS3231 to available DS1302 during M4 physical bring-up. It is now canonical software/diagnosticRTC; not an additional MCU or I2Cdevice. Pins remaincandidate/defaultsafeunassigned; no physicalRTCresult inferred. See `DS1302_BRINGUP.md`.
