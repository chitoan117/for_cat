# System requirements — M2 candidate

Requirements describe the final intended system, not a claim of physical completion. Host verification is separate from real-data/bench/full-system validation. Architecture is normal USB webcam → Jetson Nano → USB serial → ESP32-S3, existing Web/App ↔ REST.

| ID | Requirement / acceptance evidence |
| --- | --- |
| FR-001 | Identify OWNER_CAT/OTHER_CAT/OTHER_OBJECT with UNKNOWN rejection; held-out real predictions and false-acceptance study required |
| FR-002 | Track eating starts/ends/duration from positively supported temporal evidence; real labelled events required |
| FR-003 | Track drinking events/duration/frequency without volume inference; real labelled events required |
| FR-004 | Accept manual-feed intent with durable request/result/idempotency semantics; physical request remains rejected at M2 |
| FR-005 | Dispense a reviewed target with weight feedback and final verified result; physical rig required |
| FR-006 | Maintain water through calibrated sensing/hysteresis/bounded pump policy; physical rig required |
| FR-007 | Store UTC history and typed sessions recoverably; deployment persistence evidence required |
| FR-008 | Expose versioned health/status/history/feed REST contracts without raw GPIO authority |
| FR-009 | Report camera/link/sensor/model readiness honestly, retaining unknown/missing values |
| FR-010 | Explicit bounded capture with source/session metadata, no overwrite and no automatic webcam start |
| FR-011 | Validate/version datasets and prevent session/source/image split leakage |
| FR-012 | Preserve session identity through optional annotation-platform interchange; reject missing provenance |
| FR-013 | Record reproducible experiment/model metadata and evaluate supplied frame/event predictions |
| FR-014 | Produce conservative food preference/activity reports, excluding ambiguous evidence |
| NFR-001 | Bound frame/queue/DB/manifest/parser/recording resources and report truncation/budget failures |
| NFR-002 | Recover serial loss/retry without stale result acceptance or duplicate physical execution |
| NFR-003 | Keep local ESP32 safety independent of Jetson/network availability |
| NFR-004 | Reproduce host tests/builds and preserve source/config/environment/artifact provenance |
| NFR-005 | Measure latency/dropout/memory on actual target hardware; no invented FPS or latency guarantee |
| NFR-006 | Preserve frozen UART v1 and existing frontend boundaries during preparation |
| NFR-007 | Local/default-private API and trusted-local files; explicit CORS/path/input limits |
| SAFE-001 | ESP32 is final physical actuator authority; Jetson predictions cannot bypass prerequisites |
| SAFE-002 | Pump defaults OFF; invalid water evidence/timeouts clear desired pump output |
| SAFE-003 | Servo defaults safe/disabled; reboot never resumes interrupted dispensing |
| SAFE-004 | Invalid/rollback RTC rejects time-sensitive feeding |
| SAFE-005 | Weight fault/invalid/stale grams rejects or stops weight-dependent feeding |
| SAFE-006 | AI_SHADOW_MODE=true default; automatic feed authorization false at M2 |
| SAFE-007 | No production GPIO assignment or actuator enable without actual board/electrical/mechanical evidence |
| SAFE-008 | No water-volume, health diagnosis or definite food-liking claim from unsupported evidence |

Thresholds/tolerances/capacities used in code are software policies or experimental defaults until validated against real requirements; they are not scientific minimums. Traceability and V&V documents identify the remaining evidence.
