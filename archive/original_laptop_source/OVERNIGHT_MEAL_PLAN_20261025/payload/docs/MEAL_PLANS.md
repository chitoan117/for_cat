# Persistent Meal Plans and explicit SCHEDULED preview

## Operator UI

Open `/kiosk` or `/app` on the existing Jetson port8000; reload once to load the
new release. In **Cho ăn**, the Meal Plan card supports add, edit, delete and
reload. Names,24-hour HH:mm, weekdays and enabled-for-preview state persist in
the canonical SQLite. Vietnam time is UTC+7 (`Asia/Ho_Chi_Minh`), using the Jetson
clock, not an external RTC or the browser clock. New plans default OFF.

**There is no autonomous scheduler worker in this release.** Enabling a plan
only permits the **Xét lịch — DRY RUN** action. It does not turn on AUTO FEED,
servo/pump or physical feeding.35g remains the future actual-added-mass target.
No sample/real meals are created automatically. The browser verification plan
was deleted; currently there are0 active plans and one internal test tombstone.

Preview checks TIME_VALID, enabled/day, REAL connected ESP32 and safe state,
then uses the existing ScheduledRequestGate. Future -> NOT_DUE; more than60s
late -> MISSED_WINDOW_NO_CATCHUP. Eligible -> deterministic schedule_ ID, same
existing dry-run inbox and one C++ arbiter. Repeated preview of the same plan
and slot returns the same identity. It does not certify future physical-command
expiry semantics; all current execution is blocked. HX calibration is DEFERRED.
Expected current due result: DRY_RUN_BLOCKED / UNATTENDED_SAFE_MODE /
WEIGHT_NOT_CALIBRATED, actual_dispensed_grams=null and actuator_execution=false.

## Same-backend API

- `GET /api/meal-plans`: active plans, quarantined errors, preview-only mode,
  autonomous_worker_enabled=false and actuator_execution=false.
- `POST /api/meal-plans`: create with caller's unique plan_id. Same-ID/same-body
  retry is idempotent; a conflicting/deleted identity gets409.
- `PUT /api/meal-plans/{plan_id}`: full definition plus expected_revision.
- `DELETE /api/meal-plans/{plan_id}`: JSON expected_revision. Tombstone is kept;
  repeated delete is idempotent; stale revision on an active plan gets409.
- `POST /api/meal-plans/{plan_id}/preview`: JSON expected_revision. Explicit
  preview only. Eligible response includes nested canonical request/decision;
  query the existing `GET /api/feed/preview/{request_id}` for a pending result.

Create body example (configuration only):

```json
{"plan_id":"plan_operator_unique_id","name":"Bữa sáng","local_time":"07:00","weekdays":[0,1,2,3,4,5,6],"enabled":false,"target_grams":35,"timezone":"Asia/Ho_Chi_Minh"}
```

Monday=0, Sunday=6; unique nonempty days; fixed integer35 (not40 or floating35.0).
Server validates strict types, bounded names/IDs and timezone. Shared app lock
serializes config/preview operations on the existing single API process. SQLite
transactions guard optimistic revisions. Corrupt configuration is quarantined,
never scheduled. Additive meal_plans table retains user_version2 and all existing
tables. Limits:32 active plans,256 lifetime identities including tombstones;
full ledger fails closed. No automatic cleanup deletes user data.

Flutter persists request configuration on Jetson, refreshes it periodically and
uses revision checks. Old concurrent list replies cannot overwrite newer edits.
Uncertain create replies retain the same ID for explicit in-session retry;
reload fetches server state without automatically repeating a write. SCHEDULED
receipts are validated separately from MANUAL/KIOSK/APP. No mock fallback or
completed feeding event is generated from a preview.

## Verification

- Actual Jetson Python3.11:24 new tests,369 complete backend tests PASS.
- Windows Flutter: analyze NO ISSUES,25 tests PASS and release build PASS.
- Actual Jetson Chromium112/LAN: editor create default-off, disabled preview,
  edit/revision2, NOT_DUE before the slot, real due preview at23:13+07:00,
  same-ID repeated preview -> one inbox row/one C++ event. Fresh app reads the
  persisted plan, history labels SCHEDULED DRY RUN, app delete leaves0 active.
- Real feed/history tables stayed0/0/0. No external requests or runtime/network
  errors in the successful browser run. Initial harness/fixture issues were
  corrected and are not counted as physical hardware failures.

Evidence: `evidence/overnight_meal_plan_20261025T153748062876Z/` including source
and DB backups, staged/unstaged Git checkpoint, manifests, logs and screenshots.
Primary editable Flutter source D:/DA_KT_NC/feeder_demo; checkout snapshot
frontend/feeder_demo. Current artifact .native-build/flutter/meal_plans_20261025_r1.
Previous artifact real_20261025_v2 remains available for rollback via the API
drop-in; retain config/data. No firmware or protected AI component changed.

## Passive overnight observation

`for-cat-overnight-watch-20261025.service` runs scripts/watch_real_overnight.py
for8h, sampling the existing REAL API every30s. It opens no camera/serial port,
sends no control, and does not start/enable plans. Logs rotate at1MiB with3
backups (4MiB total sample budget); cumulative SUMMARY.json and up to50 error
alerts persist independently. This is periodic availability sampling, not a
measurement of every ultrasonic pulse or physical accuracy.

Live file: `evidence/overnight_meal_plan_20261025T153748062876Z/watch_8h/SUMMARY.json`.
At completion the same folder receives FINAL.json. Read status and actual
elapsed_seconds before claiming8h coverage. The original3 services and this
one-off watch are not enabled for automatic boot. If the API is briefly
unavailable during deployment, the watch records it and continues bounded reads.

The owner accepted JSN basic ranging for an approximate25cm small dorm setup;
historical timeout/outlier measurements remain available. This acceptance does
not set LOW/TARGET water geometry or enable a pump. Current invalid/null sensor
samples remain visible in the monitor and UI.
