# Architecture

Current architecture: normal USB webcam → Jetson Nano → USB serial → **ESP32-S3 N16R8 candidate** → sensors / future gated actuators. `REFERENCE_ARCHITECTURE.md` is the canonical diagram; classic MCU profiles are regression targets only.

Existing Flutter/Web ↔ REST ↔ Jetson Nano over a reviewed network. Frontend integration is not verified and the old frontend is outside this repository. Current maturity is in `CURRENT_PROJECT_STATE.md`; earlier RC/Phase descriptions below are retained as implementation chronology.

Jetson owns future OpenCV inference (OWNER_CAT, OTHER_CAT, OTHER_OBJECT), behavior observations, event history and requests. ESP32 owns final safety authorization, motion and pump operation. Never treat command receipt (ACK) as actuator success; check FEED_STATUS for final outcome. Default execution mocks camera and serial transport; real serial API mode rejects manual feed locally. HW_SAFE firmware reports REJECTED; SIM firmware now dispatches synthetic inputs through the portable policy. No physical output is enabled. Candidate ESP32-S3 N16R8 builds are official-board compile surrogates, not verified seller GPIOs.

Local bounded SQLite event history retains the newest 1,000 events by default. Typed records use explicit schema migration and a capped, fail-closed durable feed-request ledger (no ID reuse). On restart the API recovers recent states from the ledger; `/status` polls retained pending operations. Unknown/offline results remain PENDING until a valid final status arrives. If a link disappears after ACK, no new command is sent by a repeated `Idempotency-Key`. Temporal fusion and preference analytics remain data-independent research logic, not validated AI.

RC2 `ObservationPipeline` supports explicit single-frame or bounded synchronous execution with injected models. Default mocks produce UNKNOWN; no identity-only automatic feed policy exists. Canonical typed visits back compatible Event-shaped API history via read projections (no duplicate session event writes); EOF closes at last positive frame. See `RC2_ORCHESTRATION_AND_HISTORY.md`.
