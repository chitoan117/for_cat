# forr_cat — university project handoff

Local cat-activity observation and future supervised food/water control using a **normal USB webcam**, Jetson Nano and ESP32-S3. The project prepares identity/behavior tracking, validated-sensor fusion, local history and an API for an existing Web/App. It does not diagnose health or claim a cat definitely likes a food.

## Current architecture and roles

```text
NORMAL USB WEBCAM
        ↓ USB frames
JETSON NANO — Camera/OpenCV, future AI runtime, temporal behavior, SQLite, REST
        ↓ USB SERIAL — frozen UART v1
ESP32-S3 N16R8 candidate — sensors, feeding/water safety, RTC/persistence
        ↓
SENSORS / UI / SERVO / PUMP — physical actuator outputs DISABLED

Existing Flutter/Web ↔ REST API ↔ Jetson Nano
```

The webcam supplies pixels; **AI runs on Jetson**, not on the webcam. ESP32-S3 is the **final local actuator safety authority**, separate from Jetson inference/API/network failures. The seller board/memory/pins/USB routing are unverified; official S3 and classic build targets are compile/regression profiles, not alternate production architectures. **No STM32, no ESP32-CAM, no AI-camera requirement.**

## Current status — M2

**M2 — PRE-HARDWARE SOFTWARE CANDIDATE. Pre-hardware development is frozen after this handoff.**

| Verification | Result |
| --- | --- |
| Python | 301 PASS |
| Native C++ | 3271 assertions PASS: 140 safety +3131 driver |
| UART / guards / safe builds | 7/7 vectors; 18/18 guards; 11/11 profiles PASS |
| Dataset / AI / target hardware | DATASET_NOT_AVAILABLE (0 real samples); NOT TRAINED; NOT VERIFIED |
| Outputs | Actuator flags0, final GPIOs unassigned, AI_SHADOW_MODE=true |

These are host/fake-I/O/simulation/compile results, not physical sensing, feeding or AI accuracy. Normal HW_SAFE rejects physical feeds; SIM results are explicitly synthetic. ACK means receipt, not SUCCESS. Physical SERIAL API feeds are rejected locally.

Start with [current state](docs/CURRENT_PROJECT_STATE.md), [final verification baseline](docs/PRE_HARDWARE_FINAL_BASELINE.md) and [handoff report](docs/PRE_HARDWARE_HANDOFF.md). [Documentation precedence](docs/DOCUMENTATION_SOURCE_OF_TRUTH.md) labels older Phase/RC/audit records as historical.

The authorized [deep quality release](docs/PRE_HARDWARE_RELEASE_CANDIDATE.md) fixes evidenced correctness/resource defects and adds risk-based failure/generative/contract tests—not product features. Static/strict/source audit logs and source/firmware hashes are in ignored `.release/`; [quality scope](docs/RELEASE_QUALITY_SCOPE.md) documents limits. Starting217/1328 counts remain historical; actual final counts above are not forced. Hardware/data/AI milestones are unchanged.

## Repository map

| Path | Purpose |
| --- | --- |
| `jetson/app/` | FastAPI/config, camera, AI interfaces/service, temporal/fusion, analytics, SQLite and serial manager |
| `jetson/tools/` | Explicit demo/replay/capture/report/diagnostic commands |
| `ai/` | Dataset/annotation/splits/releases, experiment/candidate/inactive registry and evaluation tools; no trainer/weights bundled |
| `esp32/` | Safe firmware, portable safety, configured driver foundations, explicit diagnostics and persistence |
| `jetson/tests/`, `ai/tests/`, `esp32/test/` | Host tests and native assertions |
| `scripts/` | Isolated setup and complete check runner |
| `docs/` | Contracts, workflows, requirements, thesis drafts and handoff |
| `evidence/` | Blank instructions/layout; private actual evidence is ignored |

Detailed module map: [SOURCE_TREE_MAP.md](docs/SOURCE_TREE_MAP.md). The existing frontend is outside this repository and remains unmodified/unverified.

## Setup and complete checks

From project root on Windows, using an isolated Python environment:

```powershell
& .\scripts\setup_dev_windows.ps1 -WithOpenCV
& .\scripts\run_checks.ps1
```

Native checks also require a C++17 compiler (observed Zig0.16.0); setup/check details and host package snapshot are in [REPRODUCIBLE_ENVIRONMENT.md](docs/REPRODUCIBLE_ENVIRONMENT.md). Checks cover Python/data/video, dependencies, native safety/drivers, UART, guards and all11 safe firmware profiles. They return nonzero on failures/missing required tools and preserve complete `.checks/` logs/summary. Linux wrapper: `sh scripts/run_checks.sh`; actual Jetson compatibility remains unverified.

Compile one safe S3 image from root, **no upload**:

```powershell
& .\.tools-venv\Scripts\pio.exe run --project-dir esp32 -e esp32s3_n16r8_hw_safe_uart
```

This is the bridge-route compile surrogate. Actual board/memory/USB route must be reviewed before selecting/uploading firmware. Native-USB safe and sensor diagnostic profiles are described in the existing bring-up guides. Never select SIM as physical sensor evidence.

## Quick software demo — SYNTHETIC / MOCK ONLY

From `jetson/`:

```powershell
& ..\.venv\Scripts\python.exe -m tools.demo_replay
& ..\.venv\Scripts\python.exe -m tools.run_simulator NORMAL
# Optional local mock API, no physical worker starts automatically:
& ..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use `/api/v1/health`, `/api/v1/readiness` and documented history/status routes. The API defaults to mocks; attaching hardware does not silently enable it. [DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) and [DEMO_FAILURE_RECOVERY.md](docs/DEMO_FAILURE_RECOVERY.md) define honest presentation/fallbacks.

## Hardware starting point

Read [JETSON_FIRST_DAY.md](docs/JETSON_FIRST_DAY.md), [ESP32_S3_FIRST_FLASH.md](docs/ESP32_S3_FIRST_FLASH.md) and [M3 physical gates](docs/M3_M4_GATE_DEFINITION.md). First actual task: identify/power the real Jetson and ESP32-S3, review memory/USB/supply, then safe USB PING/GET_STATUS and unplug/replug evidence with sensors/actuators disconnected. After M3 and pin/voltage review, HX711-only testing starts via [M4_DIAGNOSTIC_COMMANDS.md](docs/M4_DIAGNOSTIC_COMMANDS.md). Driver code exists; physical calibration/control does not.

## Dataset and AI workflow

Real passive sessions → explicit bounded capture (dry-run default) → human labels → session/source/duplicate-safe splits → versioned dataset gates → recorded real experiments → inactive model registration → independent host/Jetson evaluation → shadow observations. Start with [DATA_CAPTURE_WORKFLOW.md](docs/DATA_CAPTURE_WORKFLOW.md), [ANNOTATION_GUIDELINES.md](docs/ANNOTATION_GUIDELINES.md) and [AI_RESEARCH_EXECUTION_PLAN.md](docs/AI_RESEARCH_EXECUTION_PLAN.md). No dataset download, training or production threshold selection runs automatically.

## Thesis and transfer

[Vietnamese outline](docs/THESIS_REPORT_OUTLINE_VI.md), [supported draft](docs/THESIS_DRAFT_VI.md), [blank result tables](docs/THESIS_RESULTS_TABLES.md), [presentation](docs/FINAL_PRESENTATION_STRUCTURE_VI.md), [transfer instructions](docs/PROJECT_HANDOFF.md), [release checklist](docs/RELEASE_CHECKLIST.md) and [evidence index](docs/EVIDENCE_INDEX.md).

## Known limits / stop point

No real Jetson/webcam-on-Jetson/ESP32 runtime, sensor/actuator/NVS calibration, cat corpus, trained model, TensorRT performance or full frontend demo is validated. Current AI/track/model tools are foundations, not a deployed classifier/tracker. Frozen v1 lacks production sensor telemetry; active physical control remains prohibited. API stays local by default; auth/TLS deployment is future evidence-dependent work.

**Stop pre-hardware feature development. Next evidence must come from real Jetson, ESP32-S3, sensors, camera, cat video or real training. Do not inflate progress from more fixtures/docs.**
