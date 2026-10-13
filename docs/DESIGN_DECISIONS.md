# Design decision record — current architecture

Accepted design choices describe intent and host-supported boundaries, not target performance or completed hardware. Normal USB webcam → Jetson Nano → USB serial → ESP32-S3 N16R8 candidate; Web/App ↔ Jetson REST. No active alternate MCU/camera architecture is introduced.

| ID | Decision | Rationale | Trade-off / remaining evidence |
| --- | --- | --- | --- |
| DD-01 | Jetson for vision/AI, not ESP32 inference | Separate image/runtime/storage workloads from bounded MCU safety | Nano ABI/memory/latency/model ops unverified; no FPS promise |
| DD-02 | Normal USB webcam, no AI-camera requirement | Pixels and inference are separable; camera/model choices not locked together | Actual Linux backend, mount/lighting and quality need testing |
| DD-03 | ESP32-S3 for sensors/local control instead of direct Jetson actuator GPIO | Local RTC/weight/level/persistence policy independent from app/network | Power/reset/stop behavior needs real rig; exact S3 seller board unverified |
| DD-04 | USB serial Jetson↔MCU, not MCU Wi-Fi control | Explicit local link, bounded frames/IDs/recovery; no public control path | Cable/port/reset routing and physical recovery pending |
| DD-05 | ESP32 final actuator authority | Requests/predictions cannot bypass validated sensor/time/limits/interlocks | Current outputs hard-disabled; physical readiness and durable outcomes absent |
| DD-06 | AI_SHADOW_MODE=true before future actions | Compare real predictions with humans without energizing mechanisms | Observation authority/accuracy still needs validation; M2 auto-feed false |
| DD-07 | Session/source-level split and provenance | Adjacent/derivative frames must not leak across training/evaluation | Human near-duplicate/crop lineage audit; no fixed scientific sample count |
| DD-08 | Temporal behavior, not isolated-frame event certainty | Confirm positives, bound dropout, avoid fictitious continuous eating | Boundary tolerances and confirmation policy require real annotations |
| DD-09 | REST API for existing frontend | Clear versioned status/history/request/result boundary, separate UI | Actual old-client schema/network/auth/TLS integration unverified |
| DD-10 | SQLite local history/ledger | Embedded persistence and bounded typed/generic records without server dependency | SD power-loss/capacity/backups/retention must be validated |
| DD-11 | Optional values and separate safety/calibration records | Missing evidence cannot become zero/full/healthy; sensor tuning cannot erase safety counters | Real calibration/NVS durability and source attribution pending |
| DD-12 | Frozen v1 and disabled outputs through handoff | Preserve known wire/safety regression while evidence is unavailable | V1 lacks detailed sensor telemetry/grams payload; future changes require negotiated/versioned evidence |

Source details: `SYSTEM_REQUIREMENTS.md`, `SOFTWARE_ARCHITECTURE.md`, `UART_PROTOCOL.md`, `AI_TASK_ARCHITECTURE.md`, `SECURITY_REVIEW.md`. Historical Phase/RC choices remain only as labelled checkpoints. No rationale borrows an external project's accuracy or claims physical implementation success.
