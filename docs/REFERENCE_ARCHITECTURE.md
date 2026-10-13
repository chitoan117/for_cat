# Reference architecture — CURRENT, M2 handoff

```text
NORMAL USB Webcam
    ↓
Jetson Nano
    Camera/OpenCV → injected identity/behavior model boundary
    → temporal sessions → session fusion → SQLite → REST API
    ↓ USB serial (UART v1 binary frames)
ESP32-S3 N16R8 candidate
    configured sensor/UI driver and diagnostic foundations (host/compile verified only)
    local feed/water safety → separate safety/calibration persistence
    servo/pump interfaces: physical outputs hard-disabled

Existing Flutter Web/App ↔ Jetson REST API
```

**NO STM32. NO ESP32-CAM. NO AI CAMERA REQUIRED.** A normal USB webcam supplies pixels; future trained AI runs on Jetson, not on the webcam or ESP32. No frontend recreated or modified.

This is the single current architecture. Classic `esp32dev` profiles are retained software regression/compatibility targets, not a second production architecture. The official S3 DevKitC-1 target is a compile surrogate; exact seller board, memory, pins and USB routing remain unverified. Normal USB serial connects Jetson to the MCU; direct GPIO UART and Wi-Fi MCU control are not current deployment paths.

Current implementation/status: `CURRENT_PROJECT_STATE.md`; verified counts: `PRE_HARDWARE_FINAL_BASELINE.md`; final handoff/freeze: `PRE_HARDWARE_HANDOFF.md`. SIM data/results remain synthetic. Normal HW_SAFE rejects physical feeding; explicit ASCII diagnostics are separate builds and require reviewed pin configuration before physical use. Actuator flags remain0, all final GPIOs unassigned, AI shadow mode true, dataset absent and AI untrained. No real hardware or frontend integration is certified by this diagram.
