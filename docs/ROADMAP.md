# Roadmap

- **HISTORICAL Phase 1:** API, serial contract, mocks, bounded event store and inert firmware foundation; not the current implementation inventory.
- **Phase 2 (hardware validation pending):** real Jetson USB webcam and serial transport have NOT been tested. Follow `PHASE2_MANUAL_STEPS.md`; bench-test without actuators.
- **CURRENT M2 handoff:** pre-hardware/data-AI preparation frozen; use `CURRENT_PROJECT_STATE.md` and `PRE_HARDWARE_HANDOFF.md`. Stop adding pre-hardware features/tests/architecture. Next engineering evidence must come from actual Jetson, ESP32-S3, sensor, camera, cat video or real training.
- Later approval-gated phases: calibrated sensors/interlocks and validated electrical power, supervised data collection/model evaluation, sensor fusion, existing Web/App integration through the versioned REST API. Hardware gates must pass before physical feeding.
