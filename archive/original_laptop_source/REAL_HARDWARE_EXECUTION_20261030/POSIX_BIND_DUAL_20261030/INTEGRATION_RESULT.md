# FOR_CAT — POSIX bind + dual firmware, 30/10/2026

**Actual source implemented and built offline. No production/device operation.**

## Source delivered

-`bridge/esp32_bridge.cpp`: existing full Bridge source fork, not a callback-only test surrogate. Feed-link is instantiated inside `bridge()`, with the same single fd/discover/open/exclusive-lock/read/poll loop and existing canonical Database/log/event publication. `serial_platform.h` selects real POSIX OS calls or explicitly test-only no-tty IO.
-`bridge/feed_outbox.h`: actual SQLite queue consumption/claim before write, `sole_owner_feed_link.h` binding, producer/CRC/session/sequence checks, durable consumed request IDs before FEED, validated RX persistence and status. CLAIMED/UNCERTAIN is never automatically requeued. No new tty-owning process.
-`bridge/stream_mux.h`: one RX stream demuxes atomic JSON diagnostics and UARTv1 binary frames. Mode identity is explicit; no relabeling as diag_current_hardware. `bridge_options.h` adds explicit dual/feed profiles and separate reviewed TX scope; default stays PLAN/read-only.
-`backend/outbox.py`: automation/client writes queue bytes and reads validated replies from SQLite. It has no Serial API. Existing client/ledger/AI/API code is reused; client disconnect now clears the live link even if recording UNKNOWN itself fails in SQLite.
-`firmware/src/dual_station.cpp`, candidate-local manual/diagnostic source changes: existing manual commands plus binary feed-link negotiation, using **one HX711/Serial station and one GPIO6 driver**. `servo_bus.h` gives exclusive manual/feed roles and a global latched STOP. Inactive peer OFF cannot detach the active owner; STOP cannot be undone by switching domains.
-`manual_console_dual.py`: existing human-console logic with the new exact dual identity/profile. Default PLAN; never stops services itself. It must not run alongside a Bridge that owns Serial.

Patch bases/unchanged inputs are in BASELINE.json; portable delta is SOURCE_CHANGES.patch. No locked candidate/source/image was overwritten.

## How far Bridge is really integrated

The new end-to-end test path is:

**automation → client → SQLite outbox → `esp32_bridge.cpp::bridge()` → fd-writer/mux/outbox logic → actual C++ MCU endpoint/controller → final UART result → same Bridge RX/SQLite → ledger → FastAPI ASGI GET.**

The C++ Bridge executes its real Database, queue, validation, polling-loop and teardown code. Windows tests replace only OS clock/tty/discovery and physical device IO. SQLite is a real Windows winsqlite3 engine shared with the Python reader, not a mocked Database. The fake MCU is in that same test process, not a second tty reader/owner. Trace asserts one owner open during normal operation; another Bridge on the same canonical DB is rejected by a real file lock.

The real Linux/POSIX branch also **object-compiled locally** with Linux headers, no FORCAT_BRIDGE_TEST. It was not linked/run on Linux/Jetson; ARM64/GCC7.5 target execution and real fd qualification remain **NOT_RUN**. The CI SQLite ABI include is only for tests/object checking; a real target build must use installed SQLite/json-c headers/libraries, never the compatibility include.

Default feed-link TX is disabled. A future live invocation needs explicit compatible profile, separate single-owner confirmation and a bounded owner review file with producer identity, expiry and all motion gates. Dual profile additionally hard-blocks automatic motion authority even if a review mistakenly asks for it. Backend REAL ingestion remains intentionally unavailable until a qualified live capture adapter/policy is approved; REAL is never relabeled MOCK to get past this gate. This is a remaining qualification/enablement step, not a live deployment delivered by the offline tests.

## New evidence — counts kept separate

| Evidence | Result / exact location |
|---|---|
| Full Bridge source strict C++14 compile +14 new integration cases | **PASS_OFFLINE**, `bind_tests_safety_paths/result.json`, `compile_actual_source.log`, `integration.log` |
| Actual dual firmware setup/loop,8 new cases with fake GPIO | **PASS_OFFLINE**, `dual_tests_global_stop/result.json` and per-case logs/JSON |
| New ESP32-S3 APP build/image validation | **PASS_OFFLINE**, `dual_build_global_stop/result.json`, `compile.log`, `image_info.log` |
| Real Linux/POSIX branch local x86_64 object compile | **PASS_OFFLINE compile-only**, `posix_syntax_object_only/result.json`, `compile.log`; target link/Jetson NOT_RUN |
| New dual console Python3.6 grammar/default PLAN | Checked in `posix_syntax_object_only/console_plan.log`; no Serial opened |

Fourteen cases include: CAT-at-ROI→38g final→atomic history/API; ACK not completion; duplicate FEED blocked in durable Bridge store;38g without closure remains FAULT; cable loss/lease timeout; producer/CRC/stale sequence rejection; partial write never retries; second owner denied; default PLAN; DOG abort; mixed JSON/binary dual profile INERT; unsafe JSON disconnects bound control too; stale peer not published ready; failed UNKNOWN SQLite logging cannot keep heartbeats running.

All new records/observations are **MOCK**. Scale/closure/output inputs are independent scripted fakes; not evidence that the door or HX711 moved/weighed in this run. Earlier8/11 development passes are not added to the selected14 cases. Old30/29/16/9 suites were not rerun. New cases were rerun only after new binding/global-STOP fixes. Initial missing Windows import-library and optional Zig syntax-driver failures are preserved; selected object-compile succeeded without suppressing source warnings.

## Firmware selection

| Image | Role / status |
|---|---|
| Locked manual415456bytes/SHA77faf097…aecaac93 | Existing first manual-servo candidate, unchanged. No closed-loop wire support. Still requires safe APP-only/activation approval. |
| Locked feed-link377840bytes/SHA867707f7…aeb8882 | Protocol-development INERT image; no manual station. **Not a physical E2E food image.** |
| NEW dual423712bytes/SHA below | Minimal one-APP next candidate: manual station plus feed-link control-plane in one stream, one servo bus; feed actuation/journal writes remain INERT. No extra flash is needed merely to switch between manual diagnostics and protocol negotiation after this image is separately approved/loaded. |

Selected new APP: `dual_build_global_stop/artifacts/firmware.bin`

```text
01c056e04679c6a182a0c8475b151400706455137c9ea329c9600b145e706232
```

ESP32-S3/UART0/16MB/no PSRAM; partition table matches old kit byte-for-byte. Build offset0x10000 is not running-bank proof/permission. `dual_build_safe_initial` predates the global-bus STOP latch and is retained only as development evidence. No factory/bootloader/partition/NVS/otadata artifact is handed off for writing.

Manual timing/range remain unchanged:1000–2000us electrical, span≤100us, configure once, max3arms/moves, arm2s/open250ms/close350ms/hard3s; ARM itself can move. No live pulse values/angles were guessed. Boot is DISARMED/PWMoff, pump GPIO7 untouched/INERT, buzzer GPIO2 disabled, ultrasound channels disabled. No CAT/DOG automatic action on boot/reconnect.

## Closure truth / PASS_REAL blockers

No actual gate-closed sensor/feedback is present in the reviewed GPIO map/source. LEDC attach/write/detach success and elapsed CLOSE time are commands, not physical position. Both automatic candidates currently provide `Closure.available=false`; dual additionally hard-false enables feed and uses a non-writing journal adapter. **It cannot physically auto-feed35g and must not advertise otherwise.**

Before active automatic E2E: implement/qualify an independent closure-confirmation criterion/provider (without inventing GPIO/evidence), bind a reviewed real durable journal/active profile and qualify actual MCU/Bridge capture/REAL ingestion. A settled38g alone remains FAULT if closure is unproven; the full Bridge integration test explicitly verifies that result. Bounded PWM close is never upgraded to physical closure.

Still pending physical/maintenance evidence: servo model/rating/power/GND/cutoff/safe pulse/mechanism trial; board-bound running partition/security/eFuse/antirollback and recovery/executor; four ECHO protection/peak evidence; exact accepted HX calibration coefficients/context before reset; explicit APP-only and movement approvals. Backup/rollback bytes and prior HX static accuracy remain accepted; no repeat weights/backups requested. Two pump motor wires removed from F5305S OUTPUT remain OWNER_CONFIRMED isolation, not an OFF-polarity measurement.

**Next physical step remains servo-specific model/label + V+/GND/GPIO6/cutoff evidence**, then the narrowly approved maintenance/manual small-motion trial; no automatic food cycle is authorized. No flash/reset/service change, real Serial/camera open, SSH or production HTTP/DB operation was performed. APP FLASH=NO-GO; new PASS_REAL=NONE.
