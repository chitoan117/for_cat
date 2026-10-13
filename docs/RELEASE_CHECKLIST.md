# Future milestone release checklist

Do not use this checklist to award M3–M8 from templates or more mock tests. Current baseline is M2; future release requires actual relevant evidence and instructor/team review.

- [ ] State scope and intended gate; retain no-feature pre-hardware freeze until real evidence justifies work.
- [ ] Inspect source status/diff/version where Git exists; no reset, hidden discard or invented commit. If absent, archive/hash the reviewed source manifest.
- [ ] Run `scripts/run_checks.ps1` (appropriate complete environment); save actual exit status, pytest counts/failures/skips, native counts, vectors, guards, profile results and dependencies. Do not suppress a failure.
- [ ] Inspect/backup current database using SQLite snapshot; verify schema/counts/quick_check/hash, preserve uncertain outcomes, never overwrite history silently.
- [ ] Record each actual firmware environment/flags/board/memory/USB route and SHA256 of the **exact image uploaded**, plus upload/boot/log. Build PASS alone is not board verification.
- [ ] Record actual model SHA256, task/label/preprocessing/runtime/opset/experiment/threshold/validation evidence; inactive until explicit reviewed configuration.
- [ ] Record versioned actual dataset manifest/source/sample/split hashes and integrity/leakage/coverage/diversity review; test data never used for threshold selection.
- [ ] Save physical/data/model failures as well as successes; independent commands versus actual feedback; date/time/conditions/reference/uncertainty/tolerance.
- [ ] Complete relevant evidence-index row, traceability/V&V status and result tables only from actual measurements/annotations.
- [ ] Update `CURRENT_PROJECT_STATE.md`, final baseline, handoff/release report and current diagrams together. Preserve older checkpoints as historical.
- [ ] Check privacy/secrets/access, sanitized source transfer and backup restore. No default public API exposure.
- [ ] Confirm UART v1/gates unchanged unless a separately reviewed/versioned future change is explicitly justified; no accidental servo/pump enable or guessed GPIO.
- [ ] Record reviewer decision and remaining limitations. Do not inflate a progress score from file/test count.

Future manual hashing examples (existing actual files only): PowerShell `Get-FileHash -Algorithm SHA256 -LiteralPath ACTUAL_FIRMWARE_FILE`; Linux `sha256sum ACTUAL_MODEL_FILE`. These placeholders are not hashes/evidence. An empty model/dataset or not-run physical test is recorded **NOT AVAILABLE / NOT TESTED**, not a completed checkbox.
