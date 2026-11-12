# REST API v1

Base `/api/v1`; JSON. Defaults to mocks. Real serial mode rejects physical feed commands; sensors remain NOT_CONNECTED.

RC2 compatible extension: typed observation sessions are read-projected into the existing Event-shaped history list. `/feeding-history` also includes `kind="EATING"` observations (not dispensing success), `/drinking-history` projects drinking records, `/behavior` projects all confirmed visits, and `/status.ai` distinguishes MOCK/NOT_VALIDATED/DEGRADED with `trained_model_validated=false`. No new raw-actuator or camera-start REST endpoint exists. The frozen RC1 snapshot is preserved; details of these additive projections are in `RC2_ORCHESTRATION_AND_HISTORY.md`.

| Method | Path | Response |
| --- | --- | --- |
| GET | `/health` | `{ "status": "ok" }` (process health) |
| GET | `/status` | `{ "esp32_online": true/false, "feeds": [...], "camera": "MOCK|ONLINE|OFFLINE", "esp32": "MOCK|ONLINE|OFFLINE", "sensors": "NOT_CONNECTED" }`; polls pending feed results |
| GET | `/events?limit=100` | newest-first bounded events |
| POST | `/feed/manual` | `{ "request_id": 1, "state": "PENDING" }` (202), or REJECTED/ERROR (200) |
| GET | `/behavior` | reserved stored behavior events, empty initially |
| GET | `/feeding-history` | feed transition event history |
| GET | `/drinking-history` | reserved stored drinking events, empty initially |
| GET | `/feed/manual/{request_id}` | retained authoritative state or 404; request ID 1..2^32-1 |
| GET | `/sessions/feeding`, `/sessions/drinking` | bounded typed session lists, empty by default |
| GET | `/food-types`, `/preferences` | empty initially; preferences are experimental multi-session evidence only |
| GET | `/daily-summary?day=YYYY-MM-DD` | UTC daily counts, times/durations if present, reliable grams or null |

Feed transitions are recorded as individual events: REQUEST_RECEIVED → PENDING → SUCCESS / REJECTED / ERROR. NACK produces REJECTED; connection/timeout or invalid ACK produces ERROR before acceptance. Once PENDING, an ACK, NACK or timeout during a status poll **cannot** prove success or failure; it stays PENDING. Only an explicit FEED_STATUS terminal code resolves it. The default mock never resolves by itself. `GET /health` does not test serial connectivity; use `/status` for that. `POST /feed/manual` has no body and never drives an actuator itself.

With `ESP32_TRANSPORT=SERIAL`, `/feed/manual` is deliberately rejected locally and does not transmit FEED_REQUEST. `MOCK` labels simulated devices; real modes report ONLINE only after a readable camera frame or a valid GET_STATUS response. `sensors` stays NOT_CONNECTED. The `/health` response remains process-only. A body on POST `/feed/manual` is rejected (413); optional `Idempotency-Key: [A-Za-z0-9_-]{1,64}` returns the original state across restarts while the bounded durable request ledger is available. On ledger capacity exhaustion the API fails closed (503). Polling `/status` can be slow when a device is offline; no background polling yet.

`CORS_ORIGINS` is empty by default and rejects wildcard. No authentication/TLS/public deployment exists; external clients must not infer feeding from HTTP 202 or ACK. API and typed record query limits are bounded. Source timestamps are UTC-aware and durations use monotonic time when measured live.

Daily summary distinguishes `feeding_requests` (all retained attempts) from `feeding_sessions` (SUCCESS only). If the 1,000-detail read window is exceeded, `session_details_truncated=true`, `feeding_sessions` and partial consumed-grams totals become null; preference ranking refuses truncated evidence (409 on `/preferences`). Missing sessions yield empty lists/null quantities, never fabricated zeros for unknown consumption. Simulation-only water state, when available, is named `simulated_water`; real water telemetry does not exist in v1.
