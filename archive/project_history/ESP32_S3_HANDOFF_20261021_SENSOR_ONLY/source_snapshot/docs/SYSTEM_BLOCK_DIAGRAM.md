# Final system block diagram

**Current:** `REFERENCE_ARCHITECTURE.md` is the canonical2026-10-21 target/source
boundary. C++CAT/DOG/NONE already works. ESP32-S3 is16MB/noPSRAM; current sensor
roles include approach, operationalwater, separate food/waterinventory(TBDpins),
HX711 andPIR, DS1302/OLED. One Web/backend/database/API with kiosk/app layouts.
The M2 diagram below is historical and is not evidence of current physical PASS.

```mermaid
flowchart LR
  C[Normal USB webcam] -->|USB frames| J[Jetson Nano: camera / AI boundary / sessions / SQLite / REST]
  W[Existing Flutter Web/App] <-->|REST over reviewed local network| J
  J <-->|USB serial: frozen v1 today| E[ESP32-S3 N16R8 candidate: sensors / safety / local control]
  S[HX711 / load cell / RTC / food-water sensors / button] --> E
  E --> O[OLED / active buzzer]
  E -.->|Disabled at M2; future gated outputs| A[Servo / pump driver rig]
```

**NO STM32. NO ESP32-CAM. NO AI CAMERA REQUIRED.** Webcam is ordinary USB; Jetson performs future AI inference. ESP32-S3 handles sensors and final actuator safety independently. Existing frontend is outside this tree. Seller N16R8 board and actual wiring remain candidates/unverified. No block arrow proves a deployed physical connection.

Current state: `CURRENT_PROJECT_STATE.md`; handoff/freeze: `PRE_HARDWARE_HANDOFF.md`. HX711/RTC/ultrasonic/OLED/button/buzzer are MCU peripherals; servo/pump paths remain physically disabled. Classic regression profiles are not a second current architecture.
