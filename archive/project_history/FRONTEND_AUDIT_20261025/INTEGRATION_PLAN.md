# Existing Flutter UI -> real ForCat SystemState

## Identified frontend

- User-provided source: `D:\DA_KT_NC\feeder_demo`.
- User-provided public reference: https://bua-an-cua-meo.pages.dev/.
- Flutter package: `feeder_demo`, version1.0.0+1; Dart constraint^3.13.3.
- Available SDK used for isolated audit: Dart3.13.5 under `D:\dev\flutter`.
- Not a Git checkout. Preserve original source before migration.
- All six audited original source/config files remain byte-identical after audit.
- Hosted HTML/version metadata confirms Flutter/feeder_demo. Python asset hash
  downloads received HTTP403, so deployed JS was NOT byte-matched to local build.

## Actual mock source, not an HTTP backend in this app

`lib/main.dart:2,35` imports/instantiates `MockFeederBackend` directly.
`lib/mock_backend.dart` is a ChangeNotifier/scenario state object; `feed()` waits
900ms then appends a fabricated success40g. There is no HTTP or WS client in lib.
`D:\DA_KT_NC\tools\mock_api_server.py` is a separate fixture and is not imported
or called by this two-file Flutter app.

Hardcoded demo values include food75%, water82%/12%, recognition94%, today1/3 or2/3,
40g feed label/success and assumed healthy RTC/servo/pump. Legacy hardware labels
STM32/ESP32-CAM are not the canonical Jetson/ESP32-S3 architecture.

## Source analysis result (isolated copy)

`dart analyze lib` returned2 errors and1 warning:
- main.dart:840 missing comma after the recognition switch expression arm.
- main.dart:854 normal scenario missing from the non-exhaustive switch.
- main.dart:856 duplicate ownerCat arm unreachable.

These errors exist before migration. Original files were not fixed/rewritten in
this audit. Full output and source SHA256: `dart_analyze.log`, `audit.json`.

## Preserve the design, replace the data provider

Keep the current orange/blue theme, app title, cards/dialogs and five tabs:
Tổng quan / Cho ăn / Lịch sử / Hệ thống / Cài đặt.
Introduce one backend interface with explicit MockProvider and RealHardwareProvider;
REAL is the real Jetson/demo default, no fallback to mock numbers on failure.

| Existing widget/data | Real mapping |
|---|---|
| Scenario online flag | SystemState.esp32.health/connected + actual realtime connection |
| Scenario recognition /94% | SystemState.ai.classification/confidence/health/timestamp |
| Food75% | food_reservoir_percent=null, NOT_WIRED until sensor#2 exists |
| Water82% | Separate actual water_operational distance/validity; reservoir%=null |
| Missing bowl scale info | weight.raw_counts, calibrated=false, grams=null while deferred |
| Today1/3,2/3 | Actual DB/scheduler data if supplied, otherwise unknown/not configured |
| Delayed feed success40g | Existing preview API,35g target, C++ decision, actual=null, DRY_RUN_BLOCKED |
| In-memory success strings | Actual backend events/requests; dry-run is not a completed feed |
| Assumed healthy system | Actual OLED/PIR/HX/approach/water/button and arm/AUTO/output flags |
| Scenario selector | Explicit development MOCK only; REAL shows actual connection configuration |

Use existing Jetson APIs only:
- `GET /api/status`
- `WS /api/ws/state`
- `POST /api/feed/preview`
- `GET /api/feed/preview/{request_id}`
- existing bounded status/events/history endpoints where appropriate.

Manual request must retain one ID across double-click/retry/reload, sourceMANUAL,
sub-sourceKIOSK/APP, target35g. Never simulate success or convert raw counts to grams.
Unattended mode remains physical execution=false; button/AI/web never bypass arbiter.

## Deployment path for the real demo

Build Flutter static assets on Windows, serve them through the EXISTING Jetson
backend on the same origin for `/kiosk` and `/app`. Keep one backend/SQLite/state
and the C++ USB serial owner; no frontend serial reader, ESP32 Wi-Fi or MQTT.
Bundle CanvasKit/fonts/assets locally so the Jetson screen needs no WAN/CDN.

The Cloudflare reference is HTTPS; directly fetching private HTTP/ws Jetson
endpoints from that hosted page runs into browser mixed-content/private-network
and origin constraints. CORS alone does not solve this. Prefer the same-origin
Jetson deployment for local/LAN use. Cloud-hosted remote REAL access requires the
separately scoped secure VPN/relay/HTTPS architecture, not public port forwarding.

Migration is AUDITED/PLANNED, NOT IMPLEMENTED or deployed by this audit. The current
Jetson dark pages remain working diagnostic views; this Flutter source is the
user-designated UI reference for the next frontend integration task.
