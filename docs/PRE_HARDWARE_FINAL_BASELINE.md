# CURRENT final pre-hardware baseline — verified handoff

**Milestone M2 — PRE-HARDWARE SOFTWARE CANDIDATE.** Authorized deep quality/failure-injection pass actually ran `scripts/run_checks.ps1`, returned success at runner timestamp `2026-10-05T08:47:23.028710+00:00`, status `PASSED_HOST_CHECKS`; subsequent strict/static/API/source audit passed. This is observed host time, not a sensor/cat session. Earlier documentation handoff at05:45:18.539625 had217/1328; quality starting run at05:55:03.083603 confirmed those counts. The current301/3271 reflect justified risk tests and evidenced corrections, not forced numbers or product features. UART v1 format/vectors, actuator gates, frontend and milestone remain unchanged.

**Current architecture:** normal USB webcam → Jetson Nano (camera/AI boundary/temporal/API/SQLite) → USB serial → ESP32-S3 N16R8 candidate (sensors/safety/local authority) → peripherals/future servo/pump; existing Flutter/Web ↔ REST ↔ Jetson. Exact board/memory/USB/pins unverified; classic profiles are regression targets only. No STM32/ESP32-CAM or AI-camera requirement is part of this architecture.

**Current source-of-truth pages:** `CURRENT_PROJECT_STATE.md` (human-readable maturity), `REFERENCE_ARCHITECTURE.md` / `SYSTEM_BLOCK_DIAGRAM.md` (one architecture), this actual baseline, `PRE_HARDWARE_HANDOFF.md` (freeze/next evidence), and `DOCUMENTATION_SOURCE_OF_TRUTH.md` (history/context-failure audit). Older checkpoints/`PROJECT_STATUS_CURRENT.md` remain historical.

## Exact executed verification

Command: `scripts/run_checks.ps1` → `scripts/check_release.py`.

| Check | Result / scope |
| --- | --- |
| Python | **301 passed,0 failed,0 skipped,0 errors**;84 additional parameterized/risk tests over the217 starting checkpoint |
| Native safety | **140 assertions PASS** |
| Native drivers | **3131 assertions PASS**, including seeded codec/calendar/level/corruption/fault properties |
| Native total | **3271 assertions PASS**;1943 additional checks, not1943 independent scenarios |
| UART v1 | **7/7 vectors PASS**, wire/golden files unchanged |
| Compile guards | **18/18 PASS** |
| Firmware | **11/11 profiles PASS**, PC compile only |
| Imports / dependency consistency | PASS; `pip check` no broken requirements |
| Dataset acceptance | **DATASET_NOT_AVAILABLE**, 0 repository samples |
| Capture CLI smoke (earlier productization evidence) | DRY_RUN, camera_opened=false; not rerun as physical testing in this handoff |

Profiles: `esp32dev_sim`, `esp32dev_hw_safe`, `esp32s3_n16r8_sim`, `esp32s3_n16r8_hw_safe`, `esp32s3_n16r8_hw_safe_uart`, `diag_hx711`, `diag_rtc`, `diag_i2c`, `diag_food_sensor`, `diag_water_sensor`, `diag_oled_button_buzzer`. All safe/unassigned actuator-disabled profiles. S3 is a compile surrogate, not seller-board validation.

The866/1188-driver checkpoints were earlier. Current native driver count3131 is executed output after adding bounded properties; safety140 and all7 wire vectors are retained. Two reviewed bounded C++ casts eliminate strict warnings without layout/CRC changes. Detailed quality evidence/limits: `RELEASE_QUALITY_SCOPE.md` / `BUILD_WARNING_AUDIT.md` / `DEFECT_LOG.md`.

Generated ignored `.checks/summary.json` records counts/profiles/environment; complete per-step logs include pytest/video/dataset tests, native outputs, guards and firmware output. Failures/missing compilers/tools return nonzero and print full failing output; no errors are suppressed. Updated shell wrapper is prepared but not run on Linux/Jetson.

Environment: Python3.14.3 Windows11, pytest9.1.1, OpenCV4.13.0.92, Pillow12.1.1, NumPy2.5.3, PlatformIO6.2.0, Zig0.16.0; pinned firmware `espressif32@55.3.311`/Arduino3.3.11/Xtensa14.2.0+20260121. `requirements-host-snapshot.txt` preserves observed package versions; target compatibility/security still requires review. No Git repo/revision exists here; experiment bundles record a source-tree hash instead.

## Existing implementation carried into handoff (no new features here)

The quality pass additionally corrects premature nested-frame resync, import DB side effects, terminal write atomicity, empty-body bypass, stale/subject-invalid fusion and preference evidence, temporal gaps/timing bounds, provenance/path/JSON budgets and partial-write/schema-error cleanup. These are correctness fixes to existing paths, not new endpoints/drivers/models. `docs/openapi_v1.json` freezes the observed contract. `.release/release_manifest.json` / `firmware_manifest.json` record actual source/docs/requirements/OpenAPI/binary hashes and footprints; no flash or model/data archive.

- Explicit camera/file **sampled-frame capture**, schema-v1 session manifests, duration/frame/storage/decode limits, graceful stop with a hard worker deadline, staging/no overwrite and dry-run default. No automatic physical webcam startup.
- Deterministic interval/minimum-spacing extraction, exact dedup and optional perceptual warnings; no motion-model dependency.
- Session/source/exact-hash cross-split failures, bounded near review and full release integrity gates; immutable dataset-version metadata rather than folder-name-only versions.
- Explicit consolidation of captured sessions and local classification export/import with session/source sidecar, optional returned labels and SESSION_METADATA_MISSING rejection. No upload/API key or claimed Roboflow result; detector YOLO/COCO converter remains format-specific future work.
- Candidate metadata without model downloads; validated experiment configs/bundles, source/environment/label provenance and archive of caller-supplied results/artifact hashes.
- Inactive model registration with task/label/path/hash checks; no automatic activation or promotion to VALIDATED_HOST/JETSON.
- Supplied frame metrics, macro/per-class/confusion, both identity error directions, confidence sweeps/UNKNOWN and temporal event tolerance/overlap/false/missed events. No real metric is produced without predictions; tests are labelled synthetic arithmetic.
- Supplied-track TTL/budget/attribution boundary; conservative multi-cat/overlap exclusions. Current runtime remains single-temporal-subject; a real association tracker is not implemented/validated.
- Food definition/trial confounders and read-only BEHAVIORAL PREFERENCE TREND, drinking and daily activity reports. No hunger inference, definite liking claim, water volume or health diagnosis. New detailed trial records are not automatically persisted into existing DB/API.
- Requirements, traceability, V&V, qualitative FMEA, seven sequence diagrams, block/network/software diagrams, candidate BOM/unassigned pin worksheet, Vietnamese summary/talk track and honest software/future demo scripts.
- Host dependency snapshot, unified one-command logs/summary, source/debt/security review. No risky cleanup of stable safety/frontend paths.

## Evidence stages

| Area | State |
| --- | --- |
| Software contracts/domain/tooling | Implemented + named host verification; deployment limitations documented |
| Simulation | Synthetic/mock evidence only; not actual recognition/sensor results |
| Firmware compile | All11 safe profiles PASS; no upload/runtime evidence |
| Hardware | **NOT VERIFIED**; no new physical validation |
| Dataset | **DATASET_NOT_AVAILABLE**; no downloaded/fabricated corpus |
| AI | **NOT TRAINED**, no model binaries installed/downloaded/activated, no real accuracy/FPS |
| Shadow | AI_SHADOW_MODE=true default; automatic feed authorization false |
| Actuators/GPIO | Hard disabled; final GPIOs unassigned; UART v1 frozen |
| Real-system/frontend/TensorRT | Pending actual device/data/network/integration evidence |

Prior conservative49.64% overall /66.19% software estimates are not recalculated or inflated by documentation/host tests. Baseline readiness is **qualitative preparation**, not physical completion.

## Reproduction and entry points

- `REPRODUCIBLE_ENVIRONMENT.md`, `SOURCE_TREE_MAP.md`.
- `DATA_CAPTURE_WORKFLOW.md`, `ANNOTATION_GUIDELINES.md`, `DATASET_ACCEPTANCE_GATES.md`, `PILOT_DATA_COLLECTION_PLAN.md`, `ROBOFLOW_ROUND_TRIP.md`.
- `AI_TASK_ARCHITECTURE.md`, `AI_EXPERIMENT_REPRODUCIBILITY.md`, `AI_EVALUATION_CONTRACT.md`, `AI_SHADOW_VALIDATION_PLAN.md`, `ONNX_MODEL_CONTRACT.md`, `TENSORRT_DEPLOYMENT_GATE.md`, `FOOD_ACTIVITY_REPORTS.md`.
- `SYSTEM_REQUIREMENTS.md`, `TRACEABILITY_MATRIX.md`, `VERIFICATION_VALIDATION_MATRIX.md`, `FMEA.md`, `SEQUENCE_DIAGRAMS.md`, `SYSTEM_BLOCK_DIAGRAM.md`.
- `BOM_CURRENT.md`, `PIN_TABLE_TEMPLATE.md`, `NETWORK_ARCHITECTURE.md`, `SOFTWARE_ARCHITECTURE.md`, `PROJECT_SUMMARY_VI.md`, `DEMO_SCRIPT.md`, `PRESENTATION_TALK_TRACK_VI.md`, `TECH_DEBT.md`, `SECURITY_REVIEW.md`.

## Freeze decision

**Final full regression succeeded. Handoff frozen; STOP PRE-HARDWARE DEVELOPMENT.** Remaining gates require actual device/camera/sensor/cat footage/training evidence: board/runtime/link, calibrated measurements/power/mechanics, reviewed corpus/labels, real artifacts/evaluation and integration. No more pre-hardware features/mock architecture/test inflation or manufactured results. First physical task is the real Jetson↔ESP32-S3 safe USB link with sensors/actuators disconnected, per existing M3 procedures. Milestone stays **M2**.
