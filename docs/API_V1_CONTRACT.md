# Jetson REST API v1 contract snapshot — pre-hardware RC1

Base path `/api/v1`, JSON; FastAPI application metadata version `0.1.0`. Original paths preserved. The service defaults to MOCK; hardware status is not validated. No authentication/TLS or public deployment is configured. `GET /health` is **process** health only.

| Method and endpoint | Request | Response | Relevant errors / limits |
| --- | --- | --- | --- |
| GET `/health` | none | `{"status":"ok"}` | does not probe devices |
| GET `/status` | none | `Status`: `esp32_online:bool`, `feeds:[FeedResult]`, `camera`, `esp32`, `sensors`, `link_state`, `link_stats`, `simulated_water:null|object`, `software_status:"SOFTWARE_OK"`, `hardware_validation:"HARDWARE_NOT_VALIDATED"` | offline yields OFFLINE, not false sensor health; pending polls can time out |
| GET `/events` | `limit:int=100` | newest-first `[Event]` (`kind`, UTC `timestamp`, optional `request_id/state`, bounded `details`) | limit clamped 0..retention (default 1000); noninteger 422 |
| POST `/feed/manual` | **empty body**, optional `Idempotency-Key` header `[A-Za-z0-9_-]{1,64}` | `FeedResult:{"request_id":integer,"state":string}`; 202 when PENDING, 200 for terminal REJECTED/ERROR | malformed key 400, any body 413, 30 new requests/min 429, pending/ledger capacity 503; SERIAL mode rejects locally without sending FEED_REQUEST |
| GET `/feed/manual/{request_id}` | ID integer 1..4294967295 | `FeedResult` | out-of-range 400, unknown 404, noninteger 422; no result invented |
| GET `/behavior` | none | `[Event]` for BEHAVIOR (empty by default) | bounded newest 100 |
| GET `/feeding-history` | none | `[Event]` for FEED transitions (empty initially) | bounded newest 100; not grams history |
| GET `/drinking-history` | none | `[Event]` for DRINKING (empty initially) | bounded newest 100 |
| GET `/sessions/feeding`, `/sessions/drinking` | optional `limit:int=100` | typed record arrays (empty initially) | clamped 0..min(1000, repository capacity) |
| GET `/food-types` | none | typed food-type array (empty initially) | bounded newest 100 |
| GET `/preferences` | none | experimental per-food evidence array or empty | 409 if >1000 feeding rows would truncate evidence; insufficient sessions have null trend |
| GET `/daily-summary` | optional `day:YYYY-MM-DD` (default current UTC day) | fields in `BEHAVIOR_REPORT_CONTRACT.md` | invalid day 422; unknown grams null; truncated detail flagged |

Feed states: `REQUEST_RECEIVED → PENDING → SUCCESS / REJECTED / ERROR`; failures before ACK can go directly from REQUEST_RECEIVED to REJECTED/ERROR. An ESP32 `ACK` only confirms receipt of a valid frame: **ACK != SUCCESS**. A terminal SUCCESS requires explicit correlated FEED_STATUS; a timeout after ACK stays PENDING. **Web/App must poll** `/feed/manual/{request_id}` and/or `/status` for an authoritative result when necessary; HTTP 202 is never proof of dispensing. Replay of the same `Idempotency-Key` returns its durable ledger state without resending a command, including after restart while its capped ledger remains intact. At ledger capacity the API fails closed rather than reusing request IDs.

MOCK success is only a software test outcome. `ESP32_TRANSPORT=SERIAL` prevents physical FEED_REQUEST entirely; sensors remain `NOT_CONNECTED`, and `simulated_water` appears only for the explicitly selected software twin. `CORS_ORIGINS` requires explicit origins and is empty by default. An HTTPS browser frontend cannot assume that private HTTP LAN access works; see `OLD_FRONTEND_INTEGRATION.md`. No raw servo/pump endpoint exists.
