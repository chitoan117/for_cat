# Deep quality release candidate — ACTUAL final evidence

Current architecture: normal USB webcam → Jetson Nano → USB serial → ESP32-S3 candidate → sensors/UI/future servo/pump; existing Web/App↔REST↔Jetson. No alternate MCU/camera architecture. UART v1 bytes and actuator gates remain unchanged; milestone **M2 — PRE-HARDWARE SOFTWARE CANDIDATE**.

Starting regression ACTUALLY passed at runner timestamp2026-10-05T05:55:03.083603+00:00:217 Python,1328 C++ (140+1188),UART7/7,guards18/18,builds11/11,dependencies consistent,dataset empty. This pass only addresses evidenced correctness/resource/contract defects and release tooling, not product features.

Final full `scripts/run_checks.ps1` ACTUALLY succeeded at runner timestamp2026-10-05T08:47:23.028710+00:00 (`PASSED_HOST_CHECKS`). No old count was forced:

| Check | Actual final result |
| --- | --- |
| Python |301 PASS;0 failed/skipped/errors |
| C++ |3271 assertions PASS:140 safety +3131 driver |
| UART |7/7 PASS, format/encoder/CRC/golden vectors unchanged |
| Compile guards |18/18 PASS |
| Safe firmware |11/11 BUILD PASS; no flash |
| Dependencies/imports |PASS; no broken requirements; no module-import device/on-disk DB opening |
| Static Python |Ruff selected correctness rules PASS; mypy5 selected source files PASS |
| Static/native C++ |Both harnesses PASS/executed under strict conversion/shadow/pedantic -Werror, no project warning suppression |
| API snapshot |Generated14 existing public paths; conservative contract check/runtime boundary tests PASS; no endpoints added |
| Security scan |NO_LIKELY_SECRETS_FOUND in allowlisted source/config/docs; values never printed; not global/private-file/CVE certification |
| Documentation |Internal links/named refs/anchors PASS;9 Mermaid blocks structural PASS, not browser-rendered |
| Artifact manifest |ACTUALLY generated317 hashed entries (306 allowlisted source/docs/config +11 firmware images); `--verify` PASS, no mismatches |
| Dataset/AI/hardware |DATASET_NOT_AVAILABLE (0 real samples) / NOT TRAINED / NOT VERIFIED |

The84 additional Python risk cases and1943 native property checks cover evidenced risks, not new product features or independent hardware experiments. Initial RED regressions and intermediate test/tool failures were diagnosed, corrected and rerun; no failure is suppressed. Strict/static logs and audit metadata: `.release/`; normal full-suite/build logs: `.checks/`.

Profiles: esp32dev_sim, esp32dev_hw_safe, esp32s3_n16r8_sim, esp32s3_n16r8_hw_safe, esp32s3_n16r8_hw_safe_uart, diag_hx711, diag_rtc, diag_i2c, diag_food_sensor, diag_water_sensor, diag_oled_button_buzzer. Firmware manifest includes actual binary bytes/hash and reported RAM/flash partition usage—not identified board memory or measured sensor behavior.

Artifacts exist at `.release/release_manifest.json` and `.release/firmware_manifest.json`; all11 entries have SHA256, actual firmware.bin size and build-log RAM/flash. Example bridge-safe image:336832B, RAM24164B, flash330739B; these are compile artifacts, not performance/physical measurements. Source manifest excludes secrets, venv/cache, datasets/models/evidence photos/private logs and large factory images. Re-generated and hash-verified after final report updates. No flashing.

Known limits are retained, not concealed: separate generic event-log transaction may leave a logged-history gap while durable result stays intact; native backend cannot be forcibly cancelled by a Python thread; full typing/browser rendering/CVE/legal-license/secret-absence certification was not performed. Dependencies consistent and license fields locally documented; unknown metadata stays unknown.

Quality/failure matrix: `RELEASE_QUALITY_SCOPE.md`; resolved/open issues: `DEFECT_LOG.md`; warning budget: `BUILD_WARNING_AUDIT.md`; contract snapshot/policy: `openapi_v1.json` / `API_CONTRACT_SNAPSHOT_POLICY.md`; local dependency/license metadata: `SOFTWARE_BOM.md` / `THIRD_PARTY_ATTRIBUTION.md`; privacy/naming/lab/risk/scorecard documents accompany this release.

DATASET_NOT_AVAILABLE; AI NOT TRAINED; hardware NOT VERIFIED; no GPU/real camera/flash/actuation or training performed. Metadata hashing and accelerated host fixtures are not M3–M6 evidence. Stop after final checks/manifests; next engineering evidence must be real Jetson, S3, camera, sensors/actuators, cat data or actual trained models.
