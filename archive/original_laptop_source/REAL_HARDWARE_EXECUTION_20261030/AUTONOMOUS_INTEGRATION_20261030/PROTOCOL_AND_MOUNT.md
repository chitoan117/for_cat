# Closed-loop V1 — integration boundaries / source handoff

This is a NEW application protocol, not a way to unlock `diag_manual_station`.
Existing manual image77faf097…aecaac93 and prior read-only Bridge patch stay unchanged.

## Wire

The existing UARTv1 A5 5A/version1/requestID/command/length/CRC16 envelope is reused, max256payload bytes. `uart_v1.h`, CRC/parser and hardened dispense controller are reused, not redesigned.

New command space64–74: HELLO, CONFIGURE, ARM, FEED, HEARTBEAT, ABORT, QUERY, DOG, RESULT, CAPABILITIES, INSPECT. FEED is always35g; no time-to-grams conversion exists. Legacy FEED_REQUEST3 or manual ASCII never grants closed-loop authority.

- HELLO: payload `<B I>` schema1/client nonce, outer ID equals nonce. MCU returns a request-matched CAPABILITIES,23bytes. No auto ARM/config/reset on reconnect. A new session while active aborts the old transaction.
- Every other command begins `<B I I I>`: schema1, MCU boot nonce, session, increasing command sequence. Common header13bytes. Replay/foreign session cannot launch another pulse. A request-specific FEED ID is1..0xffffff;0 is control-plane only.
- CONFIGURE:35bytes after header:4xuint16 safe_min/max/close/open_us,3xuint16 coarse/fine/settle_ms, uint8 maxpulses,5xfloat fine_threshold/tolerance/stable_range/max_target/max_dispensed. Wrapper requires span≤100us, target35/tolerance5/hardmax40 plus existing controller limits. Fixture1450/1550 values are **not approved physical presets**.
- CAPABILITIES: `<BIIIBI3BH>`: schema/boot/session/sequence/flags/lastID/pending/state/reason/calibrationID. Flags:1physical-enabled,2journal-ready,4closure-provider-available,8configured. New INERT image reports physical-disabled and no closure provider. A manual JSON mode cannot satisfy this handshake.
- ACK/NACK:15bytes, header plus original opcode/reason. ACK=accepted/PENDING only; never creates feeding history or final mass.
- RESULT:35bytes `<BIIII4BH3f>`: header plus originating session, result-code/state/reason/proof-flags/calibrationID/target/actual/latest-observed. Result codes0PENDING/1SUCCESS/3ERROR. Flags1FINAL,2SETTLED,4PWMoff,8CLOSED,16journal committed,32qualified actual mass,64calibration valid. SUCCESS requires all127, controller COMPLETE, reason0, matching calibration/request/boot/origin and30–40g inclusive. Missing measurement is null at API, not0. Non-final latest observation is separate.
- Heartbeat lease1500ms; loss/invalid sequencing can abort with bounded CLOSE then PWMoff. The existing controller also bounds pulses and total time. ABORT is processed before a pending OPEN. Wrong/late callbacks cannot overwrite an already committed conflicting final. A valid final can reconcile UNKNOWN_OUTCOME without re-sending FEED.
- Unconfirmed request/DOG/heartbeat errors invalidate the host link and stop future heartbeat refresh, so a handled transport exception cannot accidentally keep dispensing alive. Reconnect uses a new explicit handshake; QUERY may reconcile the original boot/request/origin final without repeating FEED.
- MCU journal persists pending/high-water ID in a NEW namespace only in a future explicitly enabled build; calibration namespace is not written. Pending on reboot blocks inspection/ARM/resume. Current released INERT build cannot write this journal or enable actuation. NVS/power-loss hardware durability remains unqualified.

## Sole Serial owner

`bridge/sole_owner_feed_link.h` is a tested callback injection point for the existing C++ Bridge's already-owned fd. It contains **no open/ownership/service API**. Default Review forbids TX including HELLO. Explicit maintenance/sole-owner review allows negotiation; motion additionally requires all review gates plus device enabled/journal/closure flags. A DurableStore callback must atomically consume an existing reserved ID before writeOnce. Partial write becomes UNKNOWN and is not retried. Caller must supply real durable storage and fd-owner checks; mock callback tests do not prove those on Jetson.

Do not run Python Serial beside the Bridge. The new Python `ClosedLoopClient` uses an injected byte transport; `WorkerTransport` runs the actual C++ endpoint via stdin/stdout and is ALWAYS MOCK. Its REAL transport/writer path intentionally refuses until a qualified sole-owner capture adapter is supplied. The C++ hook is **not mounted/deployed in the current POSIX service**; target build/fd glue and real capture remain NOT_RUN, not silently completed by a portable test.

## Backend / AI integration

Existing `ai_frame_contract.py::validate` is snapshotted unchanged. AutoGate requires fresh framed data, reviewed ROI_ENABLED/calibrated/eligible evidence,3new CAT frames over≥500ms, current safety/calibration context and a capable enabled MCU. FULL_FRAME/legacy stdout/stale/duplicate/retired epoch cannot trigger feeding. Generic CAT remains class-only, not OWNER_CAT. DOG aborts regardless of warning cooldown; warning requests are limited, and NONE/invalid AI does not create a feed. Visit latch and2h cooldown survive coordinator restart in sandbox SQLite; a new host boot requires review rather than resetting feeding authority.

`Ledger` commits request IDs BEFORE transport; unresolved SENT/PENDING/UNKNOWN blocks a new request. Final result/history/event share one SQLite transaction. Conflicting retries preserve original terminal data. All new writer instances are explicitly sandbox-fenced; REAL promotion is rejected. No new POST/control route is provided.

While pending, heartbeat plus request-bound QUERY updates a separate progress column (controller/servo-command phase and latest observation). It never inserts a feeding history row or makes ACK a final mass. Late progress cannot overwrite a terminal row. A GPIO6 OPEN_COMMAND is a software observation, not independent proof that the gate physically opened/closed.

Optional read-only API integration after review:

```python
from backend.api_patch import mount
mount(existing_app, reviewed_reader,
      lambda request, scope: existing_app.state.remote_policy.allowed(request.scope, scope))
```

This is a source integration example, **not executed on production**. Current sandbox uses Ledger as reader. Future live reader/writer/sole-owner transport must be qualified and reviewed before binding real data. Do not import/create the production app merely to run these tests. Routes `/api/v1/closed-loop/status`, `/history`, `/events` are GET-only, source-authorized, bounded SQLite read-only queries; no schema creation or device activity on GET.

## Flutter integration

Actual current `D:\DA_KT_NC\feeder_demo\lib/history_model.dart` accepts only dry-run feeding entries and `real_backend.dart` already handles cached state/receipts. Existing production API blocks real feed/manual under Bridge mode. Therefore new final records must not be disguised as dry-run receipts or ordinary ACKs.

`flutter/lib/closed_loop_feed_panel.dart` adds an optional typed view/controller using the existing AppCard. It consumes the above response schema, enforces35±5 and all final safety fields, preserves38g/41g/null, labels MOCK/REAL/NOT_AVAILABLE, rejects REAL inside OFFLINE_SANDBOX, clears unavailable data after error, and performs GET only. Future REAL display needs a server-verified device receipt; that contract fixture is not physical evidence. No existing backend/model/training/UI/service source was overwritten.

`flutter/lib/main.dart`/build/web are an explicitly NOT_CONNECTED component harness, not a replacement production kiosk/app. Actual connected test fixture response JSON, including sourceMOCK, is passed to Flutter tests; no fixture was uploaded or served to production.
