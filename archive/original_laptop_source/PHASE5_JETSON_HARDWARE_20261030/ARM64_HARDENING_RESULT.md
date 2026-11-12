# ARM64 hardening — NOT_RUN / BLOCKED_AUTH

Date: 2026-10-30. **ARM64_PASS is not granted.** SSH authentication failed with exit 255 before transfer/preflight/build. No target output directory, compiler result, binary hash or ARM64 `result.json` was produced by this session.

## Verified local package identity

- ZIP: 288687 bytes; SHA256 `1c3b8abaf2586d91ac468c8c632d8750bf28a72d92f91130b983cb51dd99990d`.
- Source manifest: `a92fc2586daacaabb5e931f0b8603bb1a3bd159a1cd747f43fd8b0cff0a968d4`.
- 147 archive members / 145 payload files, CRC/SHA/strict member set PASS; working payload matches.
- Standalone trusted verifier SHA256: `5338e1200423241177cb52680ca225ef499eaa8fdc622c59250394a433a0d5f6`.
- Native runner SHA256: `f2d93194ad8f29abcd24efda6714be0db7b53989e306032d7a53db40191b43e2`.
- Evidence `evidence/local_package/`: exit 0, actual command/time/hashes in `command.json`.

## Tooling audit completed from actual source

`tools/safe_release.py`: externally pinned manifest digest, bounded ZIP, exact file set/CRC/SHA, duplicate JSON/path/case/device alias rejection, no symlink/encrypted/binary members, no overwrite; validates all archive bytes before creating NEW destination. No archive code is imported before validation.

`tools/native_hardening.py`: default PLAN returns before directory creation/build; execute requires actual Linux ARM64, GCC 7.5.0 and manifest verification. Sequential `g++ -std=c++14 -O1 -Wall -Wextra -Werror`; existing json-c/sqlite3 via pkg-config, no installation.

- Fresh-build targets: safety_audit, mass_policy, session_audit, stream_bridge, behavior_hardening and whole POSIX esp32_bridge.
- Controller/output/journal adapters are fakes; transport uses file fixture. No MCU GPIO/camera/service API in these test paths.
- Candidate Bridge `main()` returns PLAN before `bridge()` unless explicit live-serial flag is supplied. Runner never supplies that flag; negative `--dog-warning 1` rejects in option parsing before live paths.
- Native runner verifies source before/after, records compiler/dependency logs, result and six binary SHA256s. No R1/R2 object mixing.

## New handoff wrapper / resource controls

`owner_arm64.py` is separate from sealed source. Default PLAN writes nothing. Execute requires NEW `/home/toan/phase5_for_cat_20261030_*`, intact transferred ZIP/verifier, active existing AI/API/Bridge, same expected Bridge executable and sole current serial owner. It refuses existing `source/`, wrong compiler, another active compiler, MemAvailable <768 MiB or free disk <256 MiB.

One compiler at a time, one allowed CPU, nice +15, child address-space cap 512 MiB. Low resources remain BLOCKED; do not stop production or add swap to force a run. It strictly extracts into `source/`, runs sealed PLAN first, then the unchanged sealed helper; captures per-command timestamps/exit/logs and compares production PID/state/binary hashes before/after success. A failed/partial output is retained and not reused blindly.

New wrapper PLAN/guard tests are **SIMULATION_PASS**, not ARM64: `evidence/handoff_tool_guards/` exit 0. `evidence/sealed_native_plan_local/` exit 0 is **Windows PLAN_ONLY**, not a target run. Old qualified Windows suites were not rerun.

## Required target evidence still missing

| Item | Status |
|---|---|
| Transfer ZIP SHA on Jetson / safe extraction / target strict verify | NOT_RUN |
| Jetson PLAN_ONLY | NOT_RUN |
| Actual compiler/dependency versions and target resource preflight | BLOCKED_AUTH |
| Five target executable tests and 24 file snapshots | NOT_RUN |
| Whole POSIX Bridge compile / default PLAN / DOG TX rejection | NOT_RUN |
| Source before/after and binary SHA256s | NOT_RUN |

Expected counts remain controller 12/101, mass 11/58, session9, behavior134, stream24; do not add layers or reuse R1 counts as hardening qualification. Exact USER-run commands and output paths are in `NEXT_USER_ACTIONS.md`. Original R2 ARM64 remains NOT_RUN independently.
