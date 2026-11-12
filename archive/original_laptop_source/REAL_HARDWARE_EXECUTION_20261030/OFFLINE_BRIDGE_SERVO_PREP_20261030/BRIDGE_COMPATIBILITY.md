# Bridge compatibility — implemented offline, not deployed

## Actual source mismatch

Reviewed on-disk production-release reference: `production_reference/telemetry.h`, copied from `PRODUCTION_INTEGRATION_20261029/release_candidate_v2/payload/jetson/device/`. It permits only `diag_current_hardware`, has4096-byte framing, requires `actuator_outputs_enabled=0`, boolean physical_pump_on and sensor-only fixed actuator states. The manual firmware emits `diag_manual_station`, a different identity/profile, nullable physical pump feedback, `automatic_actuator_outputs_enabled`, and real MANUAL state observations. Its retained fake-GPIO frames are up to4812bytes. Changing only the mode string would be incorrect/unsafe.

Jetson production binary was not inspected or changed in this offline session. Earlier real event logs already established unsupported firmware mode; they do not prove the current image is this new manual candidate.

## Patch actually prepared

`bridge/` is a NEW copy of sealed R2_OFFLINE_HARDENING_PM5 Bridge source, preserving its8192 limit, strict JSON/duplicate-key/typed sensor validation and existing DiagnosticSession. BASELINE.json records exact source paths/hashes. This is a hardened candidate base, not a claim of a clean patch against an uninspected running binary.

- `telemetry.h`, new `manual_telemetry.h`: explicit `MANUAL_STATION_READ_ONLY` policy. Default old profile still rejects manual mode. Exact kit ID/profile/schema/pins, required sensor objects, pump supported/off-level/state, servo pulse/budget/state mirrors, interlock, automatic authority, fault/physical-claim checks. Valid manual movement can be observed only under the explicit profile; it grants no transport/actuator permission.
- Native mode/profile are retained; no relabeling as diag_current_hardware. Physical pump feedback stays null. Global/automatic authority is separate from manual observed states; no false OFF/closure claim. Normalized `closed_loop_feed_capability=false`, `automatic_execution_ready=false`, `bridge_serial_tx_enabled=false`.
- `manual_session.h`: boot/session/sequence/arm/pulse-counter observation fence, explicit boot boundary, retired boot replay rejection, reconnect requires device-time progression, fault resurrection rejects. Same-uptime duplicates cannot refresh DiagnosticSession progress. This is process-lifetime fencing, not a durable MCU command journal.
- `bridge_options.h` shared by POSIX source and portable probe: new `--firmware-profile diag_manual_station`; default remains PLAN, explicit live-serial guard unchanged. `--dog-warning 1` still rejects, TX stub/feed/pump authority unchanged. No new command sender or mutation API.
- `esp32_bridge.cpp`: hooks the fence into accept/startup/connect/disconnect; clears non-live manual cache; manual button observations do not become feeding requests. No service/unit/config changes.

## Actual new tests executed

`bridge_tests_initial/result.json`, `compile.log`, `tests.log`, `native_invocations.jsonl` contain commands, UTC/exit/error evidence.

**SIMULATION_PASS:16 pytest cases**, compiling actual patched C++ parser/framer/session/CLI under C++14/O1/Wall/Wextra/Werror with existing json-c. Includes37 retained frames from the already-PASS firmware fake-GPIO logs; these are fixtures, not new real ESP32 readings and not37 extra pytest cases.

Coverage: explicit profile; old-profile safety rejection; identity/schema/missing fields; duplicate/malformed/oversize JSON/types; conflicting flags; inert/conditional pump; manual interlock; null values; fragmented frames and ASCII ACK noise; timeout/disconnect/reconnect; frozen uptime/host-clock regression; session/sequence/budget regression; new/retired boot; latched fault; CLI never enables TX.

Whole POSIX Bridge compilation/Jetson runtime/real ESP32 serial/API/UI integration remain **NOT_RUN**. No old firmware30-case suite rerun, no firmware rebuild, no live UART/camera, no production DB/service operation. Patch is offline-qualified portable code, not production deployment approval.

## CAT/DOG boundary

Existing policy headers are retained; no model/training changes. The current manual image has NO closed-loop feed command/terminal FEED_STATUS and NO automatic CAT/DOG receiver. Manual ACK must never be mapped to feed COMPLETE. Generic CAT is not owner identity. New normalization explicitly blocks treating this manual firmware as auto-feed capable. Automatic CAT-at-reviewed-FOOD_ROI → one durable request, DOG no-feed/cooldown, request-bound final35±5g ledger and paired REAL/MOCK API/UI require a separately qualified closed-loop firmware/dispatcher after manual hardware. No such execution path was enabled here; expansion deferred to the owner's servo-first steering.
