# Qualitative release risk register

Derived from `FMEA.md`, observed defect tests and remaining evidence, not arbitrary numerical risk scores. HOST mitigation is not proof of final-system safety.

| Risk | Existing mitigation/evidence | Remaining gate/status |
| --- | --- | --- |
| Jetson ABI/runtime/memory compatibility | Candidate interfaces/config; host checks | BLOCKED_HARDWARE: actual Nano/JetPack/packages/model ops |
| Camera position/lighting/occlusion | ROI/crop/UNKNOWN/ambiguity, annotation plan | BLOCKED_HARDWARE / DATA: actual placement/conditions |
| OTHER_CAT false owner accept | Explicit FAR counts/sweeps, shadow/no actuation | BLOCKED_DATA: held-out cats/calibrated threshold |
| EATING/DRINKING confusion | Frame/event metrics, temporal gap/dropout fixes | BLOCKED_DATA: human events/ROI/occlusions |
| Power sag/reset | Safe boot/inspection/no resume, output gates | BLOCKED_HARDWARE: actual rails/transients/stop |
| Servo jam/unsafe closure | Disabled PWM, limits/timeouts | BLOCKED_HARDWARE: mechanics/feedback/current/stop |
| Pump leak/stuck/dry-run | Physical OFF, fault/no-progress/max-time policy | BLOCKED_HARDWARE: isolated rig/feedback/containment |
| Sensor calibration/drift/staleness | Bounded drivers/optional readings/freshness/CRC | BLOCKED_HARDWARE: actual accuracy/geometry/timing |
| Serial disconnect/uncertain result | ID correlation/no wrap/reuse, pending recovery tests | BLOCKED_HARDWARE / DEFERRED: actual USB/reset/durable MCU outcome |
| Dataset leakage/provenance | Source/session/exact/near gates/interchange rejection | BLOCKED_DATA: real corpus/lineage/human near review |
| SD/NVS durability/DB capacity | Atomic visits/terminal records, locks/retention/write injection | BLOCKED_HARDWARE: target power loss/disk behavior; retention not disk quota |
| Native blocked IO/shutdown | Bounded join, honest FAULTED, no close under live worker | BLOCKED_HARDWARE: process-level intervention/target tests |
| Model artifact supply chain | Trusted-root/hash/task/label metadata; inactive | BLOCKED_DATA / AI: actual graph/runtime correctness, no metadata-only certification |
| Privacy/public exposure | Local API, source-only transfer, no auto upload, redacted scan | PARTIAL: actual footage/permission/network/auth/TLS decisions |

No overall reliability/accuracy/progress percentage is computed. First real gate remains actual Jetson↔ESP32-S3 safe USB communication; quality evidence does not award it.
