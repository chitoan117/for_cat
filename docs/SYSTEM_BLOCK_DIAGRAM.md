# Final system block diagram

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
