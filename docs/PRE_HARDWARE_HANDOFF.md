# Final pre-hardware handoff — forr_cat

**M2 — PRE-HARDWARE SOFTWARE CANDIDATE.** Current architecture only: normal USB webcam → Jetson Nano → USB serial → ESP32-S3 N16R8 candidate → sensors/UI/future gated servo/pump; existing Flutter/Web ↔ REST ↔ Jetson. AI belongs on Jetson; ESP32-S3 is final local actuator authority. Actual board/memory/USB/pins are unverified.

## Implemented and bounded evidence

| Evidence layer | Existing scope | Does not prove |
| --- | --- | --- |
| Software / host verified | FastAPI/config/readiness, SQLite typed/generic history/ledger, camera/file/service interfaces, temporal/fusion/preference/report logic, data/capture/release/interchange, experiment/registry/evaluation and paths | Nano deployment, actual classifier/tracker or physical outcome |
| Simulation / fake I/O | Injected frame/identity/behavior/weight/RTC/echo events; feed/water desired-state scenarios; policy faults/reset logic; generated video fixtures | Cat recognition, calibrated sensor readings, actual movement/flow |
| Compile verified | Five safe classic/S3 profiles plus six sensor/UI diagnostics; portable safety/driver/codec and Arduino adapters | Seller board compatibility, upload/runtime, GPIO/voltage/timing/NVS |
| Interfaces only / disabled | Servo/pump abstractions and hard output gates | Active PWM/switching/closure/stop/jam/mechanics |

Implemented driver foundations include HX711, DS3231, ultrasonic/food/water, SSD1306, button/buzzer, optional health/snapshot and separate calibration persistence. Normal binary HW_SAFE does not collect production sensor telemetry or execute physical feeds; diagnostics are explicit ASCII images. GPIO defaults unassigned; no compile result grants hardware HEALTHY. Frozen UART v1, safety gates and external frontend are unchanged.

## Verification baseline and final rerun

This documentation-only continuation retained the existing code/tests and did not inflate their counts. The actual final clean rerun is recorded below, with full logs/environment in `.checks/summary.json` and `PRE_HARDWARE_FINAL_BASELINE.md`.

**Final clean handoff rerun EXECUTED and PASSED:** `scripts/run_checks.ps1` → `scripts/check_release.py`, process success, runner timestamp `2026-10-05T05:45:18.539625+00:00`, `PASSED_HOST_CHECKS`. **217 Python passed /0 failed /0 skipped /0 errors;1328 native assertions PASS (140 safety +1188 driver);UART7/7;compile guards18/18;all11 safe firmware profiles PASS;imports PASS;dependency consistency PASS (“No broken requirements found”);dataset validation DATASET_NOT_AVAILABLE/0 samples.** Counts unchanged from the prior legitimate baseline. No upload/camera/model training or physical test was performed.

**Current-authoritative quality checkpoint (supersedes counts above):** authorized failure/release-engineering pass full run at `2026-10-05T08:47:23.028710+00:00` passed **301 Python /0 failed /0 skipped /0 errors;3271 native (140+3131);UART7/7;guards18/18;builds11/11;dependencies/imports PASS**, with subsequent static/strict/API/source audits PASS. No product feature/actuator/wire change; counts increased only for genuine risk coverage. Read `PRE_HARDWARE_RELEASE_CANDIDATE.md` / `RELEASE_QUALITY_SCOPE.md`; the earlier documentation-only handoff numbers are historical.

## Dataset, AI, hardware and next gates

- Dataset: **DATASET_NOT_AVAILABLE**,0 real samples. Tooling and synthetic test fixtures are not a real corpus.
- AI: **NOT TRAINED**; no actual model, accuracy, target FPS or TensorRT result. Shadow true; registry insertion inactive. Actual capture/labels and compatible framework are prerequisites for seven future experiments.
- Hardware: **NOT VERIFIED**; no new real Nano/webcam/USB/MCU/sensor/actuator/NVS evidence. Candidate S3 memory/board/pin table and power/mechanics need physical review.
- Frontend: external project, unchanged/unverified. API contracts/local demos do not prove browser/app compatibility or deployment security.

1. **First physical task / M3:** obtain/identify the real Jetson and ESP32-S3; review power, OS/Python/JetPack, memory and USB routing. With sensors/servo/pump disconnected, flash the exact reviewed HW_SAFE image and record boot, physical USB PING/GET_STATUS correlation/CRC and unplug/replug recovery. No guessed node/pin and no output enable. Use existing `JETSON_FIRST_DAY.md`, `ESP32_S3_FIRST_FLASH.md`, `M3_M4_GATE_DEFINITION.md`.
2. **M4:** only after M3 and actual pin/logic/power review, start HX711-only raw/stability/tare/known-mass/error/NVS/fault evidence, then RTC/levels/UI and later separately reviewed actuator/rig tests. Prepared code/procedures are not results.
3. **First data task / M5:** verify actual camera placement/source quality and collect small passive real sessions, human labels/uncertainty/provenance, source-safe release and exclusions; no stressful/dangerous behavior.
4. **First AI task / M6:** actual detector baseline from reviewed boxed data, then identity/threshold/behavior/temporal/fusion/preference experiments with held-out predictions/artifact/config hashes. No fake model or threshold from fixtures.

## Key risks and report/demo readiness

Remaining evidence concerns: device ABI/backends/latency, board/power/level shifting, sensor drift/range/clock/NVS, physical closure/jam/stuck pump/reset, durable outcome reconciliation, real label/diversity/leakage/OTHER false acceptance/multi-cat attribution, network/frontend/privacy. See `FMEA.md` / `TECH_DEBT.md` / `SECURITY_REVIEW.md`; no fabricated risk score or overall completion increase.

Report **design/method/software verification** is ready to write. Physical/data/model conclusions use `[CHỜ KẾT QUẢ THỰC NGHIỆM]` in `THESIS_DRAFT_VI.md` and blank `THESIS_RESULTS_TABLES.md`. Outline/figures/18-slide deck are prepared. Software demo today must say SYNTHETIC/MOCK; full hardware/real-model/client demo is not ready. Failure recovery never silently converts failed real runs into mock PASS.

## Source of truth and transfer

Start `README.md` → `CURRENT_PROJECT_STATE.md` → `REFERENCE_ARCHITECTURE.md` / `SYSTEM_BLOCK_DIAGRAM.md` → `PRE_HARDWARE_FINAL_BASELINE.md`. `DOCUMENTATION_SOURCE_OF_TRUTH.md` records invalid-patch-context diagnosis and retained historical corrections. `PROJECT_HANDOFF.md` provides reviewed source-only transfer, environment recreation, SQLite backup and separate private dataset/model/evidence handling. No caches/secrets/private corpus are automatically packaged. `RELEASE_CHECKLIST.md` / `EVIDENCE_INDEX.md` link future actual outcomes.

**Successful full regression recorded; HANDOFF FROZEN. STOP PRE-HARDWARE DEVELOPMENT.** No new drivers/services/APIs/mock architecture/test inflation, no UART change, no frontend changes, no actuator enable or invented GPIO. The next engineering evidence must be **real Jetson, real ESP32-S3, real sensor/camera, real cat video or real model training**. Milestone stays **M2** until relevant physical evidence exists.
