# Evidence index — future real gates, none awarded

Current milestone is **M2**. `.checks/summary.json` and logs plus `PRE_HARDWARE_FINAL_BASELINE.md` describe host verification only; generated test images/predictions/native fake I/O cannot occupy physical/real-data result rows. Existing `evidence/README.md` is a blank private layout, not a log of tests.

| Gate | Actual evidence required | Intended locations/artifacts | Status |
| --- | --- | --- | --- |
| M3 — REAL Jetson↔REAL ESP32-S3 communication | Actual device/environment/power identity, reviewed safe source/image/hash, flash/boot, USB PING/GET_STATUS IDs/CRC, unplug/offline/replug/recovery and timings | `evidence/jetson`, `esp32`, `serial`; exact criteria in `M3_M4_GATE_DEFINITION.md` | NOT PASSED |
| M4 — REAL sensors/actuators | Reviewed pins/rails/mechanics, raw/calibration/error/fault/RTC/NVS, separate safe servo/pump stop/jam/timeout/power tests, basic integrated rigs and recovery | `evidence/hx711`, `rtc`, `food_sensor`, `water_sensor`, `servo`, `pump`, `esp32`; real result worksheets | NOT PASSED |
| M5 — REAL dataset | Actual consented/passive sessions, source manifests/hashes, annotations/disagreements/ambiguity, grouped splits, integrity/leakage/diversity/usable review and versioned release | Private raw/capture/processed metadata and release record, not public source; evidence references link to real corpus | DATASET_NOT_AVAILABLE |
| M6 — REAL AI validation | Actual training config/source/environment/dataset/label map, artifact hash, held-out predictions/confusion/FAR/FRR/events/threshold rationale and target runtime/shadow evidence | Private experiment/result/artifact registry and evaluation reports; Jetson logs for any target claim | NOT TRAINED / NOT VALIDATED |
| M7 — real integrated prototype (future scope to confirm) | Synchronized actual camera/subject/events/sensors/outcomes/local safety, persistent API/history and actual existing client under faults/reboots | Reviewed joined rig/session/API/client logs; timestamps/hashes and exclusions | NOT TESTED |
| M8 — final demonstration/report (future scope to confirm) | Reviewed end-to-end real demo, known failure/recovery, report figures/tables backed by actual artifacts and repeatability | Sanitized final demo/report bundle pointing to underlying evidence | NOT TESTED |

M3/M4 exact definitions are retained in the existing gate document. M5/M6 labels follow the handoff's data/AI gates. M7/M8 are future integration/demo evidence buckets requiring agreed acceptance scope, not newly passed or secretly redefined milestones.

Each evidence item needs: unique ID/time/timezone, observer, exact hardware/source/session/track, software/config/firmware/model/dataset versions and hashes, command/procedure, expected versus **actual** result, units/reference/conditions/uncertainty, PASS/FAIL/NOT TESTED against documented criteria, raw log/photo/video paths and exclusion/failure notes. Preserve private originals and share only reviewed copies. Blank `—`, planned filenames or a filled template without actual observations are not evidence.

Report-ready blank tables: `THESIS_RESULTS_TABLES.md`; capture/data protocol: `DATA_CAPTURE_WORKFLOW.md`; real experiment order: `AI_RESEARCH_EXECUTION_PLAN.md`. No measurements, photos, cat events or model metrics were fabricated in this handoff.
