# Documentation source of truth — handoff audit

## Authority and precedence

1. `REFERENCE_ARCHITECTURE.md`: **one current hardware/system architecture**.
2. `CURRENT_PROJECT_STATE.md`: **current maturity**; actual current counts301/3271/7/18/11 corroborated by `PRE_HARDWARE_FINAL_BASELINE.md`, `PRE_HARDWARE_RELEASE_CANDIDATE.md` and `.checks/summary.json`/quality logs.
3. `PRE_HARDWARE_HANDOFF.md`: **handoff/freeze decision and next evidence**, not new functionality.
4. `UART_PROTOCOL.md` / shared golden CSV and code: frozen v1 wire contract; `API_V1_CONTRACT.md`: frontend API contract.
5. Domain workflows/requirements are procedures/design evidence. They are not physical/data/model results.
6. Phase/RC/audit checkpoints and `PROJECT_STATUS_CURRENT.md` are **HISTORICAL / NOT CURRENT**; old counts/“authoritative”/absence statements describe their original runs only.

When editing after new **real** evidence, update the current state, release/evidence reference and handoff together. Keep dated historical records; do not silently replace old measurements or turn templates into PASS evidence.

## Audit findings and resolution

### Patch failure and continuation work log

The failed step was `apply_patch` context verification, not a test/build/dependency failure. In `docs/SIMULATION_FIRMWARE_PARITY.md`, the patch expected `# Simulation and firmware parity`; the actual first line is `# Python simulator ↔ ESP32 portable-policy parity (RC1)`. The failed batch did not apply; a corrected retry preserved the other valid historical/current-source corrections. A later aborted tool invocation did not complete the handoff files. This continuation inspected the actual file/README/source-of-truth/current check summary, applied the missing annotation against the real heading, and retained successful earlier changes. No reset, warning filter, test suppression or application refactor was used. Final full verification is recorded in `PRE_HARDWARE_HANDOFF.md` after execution.

**Closure:** actual final `scripts/run_checks.ps1` succeeded, runner timestamp `2026-10-05T05:45:18.539625+00:00`;217 Python,1328 native assertions,7 UART vectors,18 guards,11 firmware profiles PASS; dependencies consistent, dataset absent. The context defect is resolved; no unexplained verification failure remains. Handoff frozen at M2.

That closure is a **historical handoff checkpoint**. The subsequently authorized deep quality pass confirmed217/1328 at start, then added risk-based checks/defect fixes and executed301 Python/3271 native,7 vectors,18 guards,11 builds PASS at08:47:23.028710. No product features or physical milestone; release candidate/manifest is the latest verification evidence.

| Contradiction/ambiguity | Resolution |
| --- | --- |
| Several checkpoint counts called current (38/88/99/125/163/170/217) | History banners/ledger labels; current quality baseline301 Python,3271 native,7 UART,18 guards,11 builds |
| Old RC1 referred to as current authority | `PRE_HARDWARE_BASELINE.md` now points to current state/final baseline |
| Old status ledger mixes historical tables with current headings | Labelled historical; compact authoritative state moved to `CURRENT_PROJECT_STATE.md` |
| Generic/classic ESP32 references versus seller S3 candidate | Canonical target ESP32-S3 N16R8 candidate; classic profiles are compatibility/regression only; old BOM labelled draft history |
| Reference architecture still says real drivers are future | Updated to existing configured foundations, physical verification pending |
| Old bring-up documents say no sensor/UI diagnostics exist | Historical-availability callouts point to `M4_DIAGNOSTIC_COMMANDS.md`; normal binary HW_SAFE remains non-measuring |
| Hardware plan offers direct GPIO UART as if current | Marked HISTORICAL / NOT CURRENT alternative; current Jetson link is USB serial |
| Physical test plan suggests classic firmware for S3 | Corrected to reviewed S3 safe profile/USB route; no pin/memory assumption |
| Inference plan says crop/detector boundary absent | Historical RC2 scope labelled; actual model/executor/Jetson validation still absent |
| Research phases versus exact future experiment order | `AI_RESEARCH_EXECUTION_PLAN.md` is current experimental order; older high-level AI phases remain history |
| High synthetic host-overhead FPS could be mistaken for Nano FPS | Checkpoint explicitly historical/tiny-fixture overhead, excluded from thesis target-performance results |
| M3/M4 preparation could be mistaken for passed milestones | Current state/evidence index explicitly record M2 and no real milestone PASS |

Search of documentation found STM32/ESP32-CAM/AI-camera references only as exclusions, not an active alternate architecture. Current architecture: normal USB webcam → Jetson Nano → USB serial → ESP32-S3 N16R8 candidate → sensors/future gated actuators; existing Flutter/Web ↔ REST ↔ Jetson. No source code/tests/protocol/output flags changed in this handoff pass. Historical material is retained; no fake evidence is inserted.
