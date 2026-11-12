# FOR_CAT autonomous integration — 30/10/2026

**Software integration advanced with actual code/build/tests. No device/production operation.**
Workspace: `D:\for_cat\REAL_HARDWARE_EXECUTION_20261030\AUTONOMOUS_INTEGRATION_20261030`.

## Implemented

| Layer | New code / reused source |
|---|---|
| ESP32 transaction protocol | `firmware/include/feed_link.h`: boot/session/sequence fencing, fixed35g FEED, ACK vs terminal RESULT, query/abort, heartbeat loss, durable-ID/journal boundary; reuses hardened `m4/dispense_bench.h` unchanged |
| MCU HAL/build | `firmware/src/closed_loop.cpp`: existing HX711/GPIO6 LEDC, nonblocking UART, calibration read-only, new journal namespace; pump7 untouched; buzzer disabled by default; no invented closure feedback |
| Sole-owner Bridge hook | `bridge/sole_owner_feed_link.h`: default no TX, reviewed existing-fd writer/store callbacks, consumes reserved ID before one write, no partial-write retry; no tty open or service action |
| Jetson client | `backend/wire.py`, `contract.py`, `client.py`: existing framing/CRC/stream decoder with distinct command space, capabilities/authority gate, request-bound completion, no FEED resend after uncertainty |
| CAT/DOG | `backend/automation.py` + unchanged existing AI validator: reviewed FOOD_ROI, fresh ordered evidence, durable one-per-visit latch/cooldown, DOG abort independent of buzzer cooldown, no identity/training claims |
| SQLite/API | `backend/ledger.py`, `api_patch.py`: durable reserve before send, atomic final/history/event, idempotency/conflict/restart handling; optional authenticated GET-only reader patch; REAL writer remains gated/unavailable |
| Web | `flutter/lib/closed_loop_feed_panel.dart`: typed final result/source/null handling, actual grams, safety flags, GET controller; existing UI helpers reused |
| Servo manual | Existing source/commands reviewed; latest actual procedure remains `..\OFFLINE_BRIDGE_SERVO_PREP_20261030\SERVO_TEST_READY.md`. No change to the locked manual image/30 tests. |

## Evidence executed — counts not added across layers

| Qualification | State | Exact logs/results |
|---|---|---|
| C++14 protocol/controller strict compilation +29 new pytest integration cases | **PASS_OFFLINE** | `tests_command_progress/result.json`, `native_compile.log`, `integration.log` |
| New sole-owner Bridge callback core:17 assertions | **PASS_OFFLINE** | `bridge_link_tests/result.json`, `compile.log`, `test.log` |
| ESP32-S3/Xtensa INERT protocol APP build + image validation | **PASS_OFFLINE** | `firmware_build_inert_macro_fixed/result.json`, `compile.log`, `image_info.log` |
|9 new Flutter tests / analyze / release Web build | **PASS_OFFLINE** | `flutter_command_progress/result.json`, `tests.log`, `analyze.log`, `build_web.log` |
| AI CAT/DOG smooth operation; HX711 static accuracy; pump motor isolation | **OWNER_REPORTED** prior/current accepted scope retained | Existing acceptance and owner confirmation; no retraining/reweigh/re-isolation request |
| New protocol on real ESP32 / sole-owner Jetson runtime / physical food / live API/Web | **NOT_RUN / BLOCKED** | No new PASS_REAL claim |

Connected test actually passes synthetic framed CAT/FOOD_ROI evidence through the new host sender, UART byte/CRC encoding, **C++ endpoint and reused controller**, fake independent scale/closure/output observations, terminal reply decoding, SQLite transaction, actual FastAPI ASGI request and then Flutter using its response fixture. All produced rows are **MOCK**. This is not camera/Serial/physical E2E.

Cases cover: ACK not completion; actual38/30/40; persistent30 not aim;41overshoot; closure missing; calibration change/stale scale; replay/duplicate request; CRC/fragmentation; link loss; MCU reboot pending; ACK loss and authoritative final reconciliation; journal failure; atomic SQL rollback/query recovery; CAT frame/epoch/visit latch; DOG abort/cooldown; manual/disabled firmware blocked; source promotion refused. Request-bound progress is also queried/persisted without creating history; Web exposes GPIO6 command phase explicitly as **not physical door-position feedback**.

An initial target compile exposed collision with Arduino macro `DISABLED`; the new enum name was corrected without changing wire code100. Failed output retained at `firmware_build_inert_initial/`. Final source rebuilt/tested into NEW folders. A subsequent client-side guard fixes unconfirmed DOG/heartbeat/request errors: stop refreshing the link lease, record UNKNOWN and do not resend; two dedicated failure regressions were added. An additive progress/API/UI change then added one integration and one widget case. Original30 firmware regressions,16 previous manual-Bridge cases, ARM64/AI suites were not rerun. Earlier20/26/28 development runs are not added to the final29-case count. No additional firmware build was needed for the host/UI-only progress change.

`FINAL_RESULT.json` and `SOURCE_CHANGES_FINAL.patch` are the current final receipt/patch. The earlier `RESULT.json`/`SOURCE_CHANGES.patch` describe the preserved pre-progress development snapshot, not current-source integrity.

## New image — not approved to flash or to replace the servo bench

`firmware_build_inert_macro_fixed/artifacts/firmware.bin`

-377840bytes; SHA256 `867707f7b260224b04a797d05142615d51ac83bfef22e6011dba573f2aeb8882`.
-ESP32-S3/UART0/16MB/no PSRAM, unchanged partition table, secure_version0. Build app offset0x10000 is **not actual running-bank proof**.
-**FORCAT_FEED_PHYSICAL_ENABLE=0**, **FORCAT_FEED_BUZZER_ENABLE=0**. No enabling option in the build runner. The supplied hardware closure provider is unavailable, so real closed-loop ARM stays blocked even if someone changes only the physical flag. No guessed closure sensor/GPIO was added.
-The dedicated future journal can be written only in an enabled/reviewed implementation; current inert build cannot write it. No calibration NVS write/migration or tare/refit command was added.

For the FIRST supervised servo trial, retain existing `INTEGRATED_MANUAL_CANDIDATE/build_safe_txatomic/artifacts/firmware.bin`,415456bytes/SHA77faf097…aecaac93. The old image/source are untouched. Do not substitute this protocol-development image to skip manual qualification.

## Remaining physical AND runtime-integration gaps

1. Servo model/rated voltage, actual source/GND/cutoff and reviewed starting pulses/mechanical clearance. Existing manual span≤100us is not proof of full gate travel. ARM can move immediately. Need a small-motion result before claiming CLOSED→OPEN→CLOSED.
2. Actual running partition, board-bound security/eFuse/antirollback, recovery/executor and APP-only approval; ECHO protection/peaks; exact calibration context before reset. Static accuracy PASS does not prove RAM persistence. Preserve exact values, not approximate offset; no repeated weight series requested.
3. Automatic closure/settling/mechanism qualification is not available. PWMoff or a mass in30–40g is not proof of closure. The independent Closure interface has no invented real implementation; closed-loop physical activation is therefore blocked.
4. The C++ Bridge hook has not been bound to production fd/database callbacks or built/run on Jetson. Live capture/REAL writer and existing FastAPI/Flutter mounting remain separately reviewed integration work, **not completed by the mock transport tests**. No service/unit/production DB modification was made.
5. Real framed/reviewed FOOD_ROI producer metadata must be confirmed before automatic CAT qualification; smooth generic CAT/DOG inference is preserved, not retrained or relabeled OWNER_CAT. Buzzer/pump physical verification remains separate; two motor wires already removed from F5305S OUTPUT are accepted isolation for servo.

## Exact next physical step

**Owner provides servo model/label and one wiring photo showing servo V+ from5V, GND reference to ESP32, GPIO6 and the independent servo-load cutoff, with mechanism clear/no food.** Do not energize/reset/open Serial for that photo; no need to disconnect the pump again. This identifies the real voltage/pulse/cutoff path, so the next measurement/activation can be specific.

After those gates and a separately approved APP-only window, verify the original manual image/hash/boot; then separately approve first movement. Conditional manual-console flow is SESSION → reviewed configure values → `SEND servo arm YES` → `SEND servo open` within2s → automatic250ms OPEN/350ms CLOSE/PWMoff. Pulse values are NOT chosen from the mock fixture. Observe the white gate physically, save video/status/pulses, use STOP plus external load cutoff on abnormal motion. No automatic food cycle is authorized by this report.

**APP FLASH NO-GO. No flash/reset/Serial/camera/service/control/API-production request executed. No new PASS_REAL.**
