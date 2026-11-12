# Phase 1.5 baseline audit

Historical navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL / NOT CURRENT:** preserves an earlier implementation/Python-compatibility checkpoint, not current feature availability or test counts. Use `CURRENT_PROJECT_STATE.md` / `REPRODUCIBLE_ENVIRONMENT.md`.

## Scope and state

No real webcam, ESP32 transport, actuator, inference or frontend integration is implemented. Python unit/API tests inject `InMemoryEventStore`; the default running API uses `SQLiteEventStore` in `jetson/data/events.db`. `EventStore` is a structural protocol (`jetson/app/storage/event_store.py`); both stores bound retention to `max_events` (default 1,000). The SQLite store prunes on append and reopening with a reduced limit; the memory store uses a bounded deque. Pruned feed history cannot be recovered after restart. This is an inert Phase 1 limitation, not a production idempotency guarantee.

## Python compatibility

Minimum practical Python version: **3.11** (standard-library `enum.StrEnum`; type unions also require 3.10). No Python 3.14-only syntax or APIs are used. The test environment uses Python 3.14.3; Python 3.11 and Jetson Nano Python compatibility have **not** been tested on a real Jetson. Dependency wheels and runtime support on Jetson remain unvalidated.

## API and history

`jetson/app/api/routes.py` provides GET `/api/v1/health`, `/status`, `/events`, `/behavior`, `/feeding-history`, `/drinking-history` and POST `/feed/manual`. Empty history routes return JSON `[]` (a structured list) without invented observations. Tests are in `jetson/tests/test_api.py`. `ACK` changes REQUEST_RECEIVED to PENDING, not SUCCESS. Only an explicit terminal FEED_STATUS can complete an acknowledged request; failures before ACK can transition directly to ERROR/REJECTED.

## Protocol cross-check (static source review)

`jetson/app/serial_link/protocol.py` and `esp32/src/main.cpp` agree:

| Element | Both sides |
| --- | --- |
| START | `A5 5A` |
| VERSION | `01` |
| REQUEST_ID | unsigned 32-bit little-endian |
| COMMAND | unsigned 8-bit, PING=1, GET_STATUS=2, FEED_REQUEST=3, FEED_STATUS=4, SYSTEM_STATUS=5, ACK=6, NACK=7 |
| PAYLOAD_LENGTH | unsigned 16-bit little-endian |
| MAX_PAYLOAD | 256 bytes |
| CRC | CRC-16/CCITT-FALSE; poly 0x1021, init 0xFFFF, unreflected, xorout 0; covers VERSION..PAYLOAD |
| CRC byte order | unsigned 16-bit little-endian |

`jetson/tests/test_protocol.py` has CRC standard vector `123456789` → `29B1` and fixed frame vector `a55a017856341203000023b6`, as well as malformed/unknown command and invalid-length cases. The ESP32 implementation is source-reviewed, **not compiled or tested against a device**.

## Static ESP32 notes

`esp32/platformio.ini` selects `espressif32`, board `esp32dev`, Arduino and 115200 baud. `esp32/src/main.cpp` uses incremental, budgeted receive parsing, an incomplete-frame timeout, fixed 268-byte buffer, CRC and version checks, correlated request IDs, ACK/NACK and FEED_STATUS. On malformed/oversized frames it NACKs and resets; on a truncated frame it resets after 250 ms. A declared but incorrect in-range payload length can delay resynchronization until the timeout or the declared frame length arrives; continuous malformed traffic and `Serial.write` backpressure have not been device-tested. FEED_REQUEST gets ACK then an explicit REJECTED result; no GPIO actuators are enabled. The 16-entry feed ID cache is volatile, so durable idempotency is required before actual feeding. PlatformIO is absent in this audit environment; no compilation claim is made.

Run verification from `jetson/` with `python -m pytest tests -q`. See `ESP32_BUILD_CHECKLIST.md` before any future device compilation and `ROADMAP.md` for approval-gated next steps.
