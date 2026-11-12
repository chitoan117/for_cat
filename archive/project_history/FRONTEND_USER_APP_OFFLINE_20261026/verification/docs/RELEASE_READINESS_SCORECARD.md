# Release readiness scorecard — M2 only

| Readiness area | Status | Evidence / boundary |
| --- | --- | --- |
| SOFTWARE READINESS | READY for host release candidate; target integration PARTIAL | Regression/static/native/contract/path/failure evidence in release candidate report; real defects fixed |
| HARDWARE READINESS | BLOCKED | Actual Jetson/S3/camera/sensors/actuators/power/NVS unverified, GPIO unassigned/output0 |
| DATA READINESS | NOT READY | DATASET_NOT_AVAILABLE; tooling/fixtures only |
| AI READINESS | BLOCKED | NOT TRAINED; no actual model/held-out/Jetson/TensorRT result; inactive registry/shadow |
| DEMO READINESS | READY software/mock; NOT READY full real demo | Existing labelled synthetic demo and report materials; actual device/cat/model/client evidence absent |
| RELEASE REPRODUCIBILITY | READY host, PARTIAL target | Source/firmware/OpenAPI/requirements/docs hashes + installed metadata; no fabricated commit/license/security certificate |

No single percentage merges these statuses. Accelerated sparse host soak and strict compilation do not establish hardware reliability. Current architecture stays normal USB webcam→Jetson→USB serial→ESP32-S3 candidate; Web/App↔REST↔Jetson. Milestone **M2 — PRE-HARDWARE SOFTWARE CANDIDATE**. Stop after final checks/manifests; next evidence must be real devices/cat data/training.
