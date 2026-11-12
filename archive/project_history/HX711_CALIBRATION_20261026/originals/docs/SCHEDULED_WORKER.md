# Scheduled Worker — DRY RUN only

## Result and boundary

**SOFTWARE PASS; DRY RUN PASS; PHYSICAL NOT TESTED / BLOCKED.**

The worker autonomously produces due SCHEDULED requests, target35g, for the
existing C++ arbiter. It never calls servo/pump/serial/camera/physical feed APIs.
AUTO_FEED/AUTO_WATER/arm flags remain false, output enable0. No physical feed
completion is recorded; actual_dispensed_grams stays null and HX gram calibration
is DEFERRED. AI C++ source/binary/engine and ESP32 firmware remain unchanged.

## Runtime and operator steps

One task named `scheduled-dry-run-worker` starts/stops with the existing FastAPI
lifespan in **for-cat-api.service**, not a second backend or systemd scheduler.
The API's installed additive drop-in is:

```ini
# ~/.config/systemd/user/for-cat-api.service.d/50-scheduled-dry-run.conf
[Service]
Environment=SCHEDULED_DRY_RUN_WORKER_ENABLED=1
Environment=SCHEDULED_DRY_RUN_POLL_SECONDS=2
```

The source template is deploy/systemd/50-scheduled-dry-run.conf. Library/test
default is disabled; enabling requires REAL SystemState and existing C++ bridge.
Invalid configuration fails before opening the database. Poll range1..30s.

Open `http://server-jetson.local:8000/app` or `/kiosk` (observedIPv4
192.168.123.8). Reload once. In Cho ăn create a Meal Plan, select Vietnam HH:mm,
weekdays and enable it. New plans default off. The worker uses the Jetson system
clock in fixed Vietnam UTC+7, not the browser clock. The UI may be closed; no
preview click is required. Existing preview remains useful and uses the same
submission logic. Worker state and the last20 persisted occurrences are exposed;
UI shows5, origin Tự động/Preview, IDs and C++ blocked reason. No healthy fallback
is manufactured if worker/network data is missing. Session counters reset with
API restart; persisted occurrences/decisions do not.

Check on Jetson:

```sh
systemctl --user status for-cat-api for-cat-esp32-bridge for-cat-ai --no-pager
curl -s http://127.0.0.1:8000/api/meal-plans/worker
journalctl _SYSTEMD_USER_UNIT=for-cat-api.service --since=-10min --no-pager
```

Expected worker.enabled/running=true, mode=DRY_RUN_ONLY, last_poll_at advancing,
error_count/last_error and actual recent_occurrences. A sample row must have
originWORKER, sourceSCHEDULED in its request/decision, target35, and blocked
decision/actuatorfalse. Hardware safety is read independently from `/api/status`.
The existing API unit is boot-enabled with user Linger=yes.

## Shared logic, identity and retries

- `evaluate_schedule`: shared Vietnam day/HH:mm, enabled/day, TIME_VALID,
  fresh REAL ESP32 and disarmed checks. Eligible only within60s of today's slot;
  future/disabled/deleted/missed/unsafe/unavailable plans never enqueue.
- `ScheduledOccurrences.submit`: authoritative re-read of current plan/revision
  under BEGIN IMMEDIATE; worker and preview use this same path. Clock is rechecked
  after acquiring SQLite write ownership.
- Each plan is one daily slot. Occurrence identity is plan_id + Vietnam local_date,
  independent of revision. At most one submission per plan/date, including time
  edits after that day's first submission. To represent multiple daily meals,
  use separate plans. Editing an already-served plan does not authorize a second
  occurrence that day; the new slot applies on subsequent matching dates.
- The canonical request ID remains the existing ScheduledRequestGate's stable
  schedule_ hash of plan_id/due epoch. The first persisted occurrence pins that
  request identity; retiming/revision/retry returns the original one.
- Occurrence and existing feed_dry_run_requests row commit in ONE transaction.
  Crash/failure before commit rolls both back; after commit a restarted process
  sees both. Concurrent worker/preview/process contenders serialize in SQLite
  and reuse the same row. No separate hardware arbiter was added.
- Temporary failures are retried only while still eligible; after the window
  there is no missed-meal burst. Queue/ledger full or corrupt config is fail-closed
  and visible as DEGRADED/error; no identity eviction silently permits replay.

Additive scheduled_occurrences columns include occurrence_id, plan_id,
local_date, due_unix_ms, plan_revision, request_id, created_at and origin, with
unique plan/date and request ID. SQLite user_version2 is unchanged. Maximum256
occurrences/inbox rows (inbox includes other existing request sources); existing
plan limits32 active/256 identities remain. Data is not automatically deleted.

## Live evidence — 26Oct2026,10:20 Vietnam

Two enabled test plans at10:20 plus one disabled same-time plan were configured
through the existing CRUD API. No preview/feed POST occurred before automatic
proof. At10:20:01 the background worker committed:

| Plan | Canonical request | Inbox / C++ event |
|---|---|---|
| worker_proof_cd006817c8_a | schedule_7996f4ce027cdc591d2564d57a9e5e8b5dc2356ea5ead400 | 1 / 1 |
| worker_proof_cd006817c8_b | schedule_692bbd1f02c911c3322da10586cdbff69631bda8db651019 | 1 / 1 |
| worker_proof_cd006817c8_disabled | none | 0 / 0 |

Both originsWORKER and decisions DRY_RUN_BLOCKED / UNATTENDED_SAFE_MODE /
WEIGHT_NOT_CALIBRATED. Repeated polls left the same2 rows/events. API restart
changed PID20482->22570 and worker identity; new session submitted_count0,
duplicate_observations4, same durable occurrences. A later name/revision edit
and preview returned the original identity. The3 test plans were deleted;
their tombstones and the2 occurrence receipts remain. Real feeding tables were
0/0/0 before and after. No physical actuation took place.

Evidence root: `evidence/scheduled_worker_20261026T021542321284Z/`:

- `live_worker_verified.json`, `live_automatic_before_restart.json` and
  `live_http_calls.json`: phase ordering, no-preview proof and saved receipts.
- `scheduled_creation_journal_lines.json`: exactly one creation log per request.
- `live_worker_journal.log`: API/worker journal; failed first ISO timestamp
  collection is kept separately (old systemd required a different timestamp form).
- `worker_ui_verified.json`, kiosk/app screenshots: actual RUNNING and automatic
  history visible, no control POST/runtime/network errors.
- DB/source backups, staged index/AI hashes, source/asset manifests, full logs.

## Regression coverage

399 backend tests PASS on actual Jetson Python3.11 (30 new worker cases).
Coverage includes all requested future/due/repeat/restart/disabled/deleted/
same-time-multiple/revision/timezone/arbiter/disarmed cases, plus concurrent
submitters, atomic rollback injection, bounded full inbox retry, shared preview,
clock-after-lock recheck, ASGI lifecycle and invalid environment startup.
Actual C++ arbiter is exercised with a synthetic PTY, then confirmed live above.

Existing UBSan fake dispense regression:9 named/99 assertions and9 additional
35g checks PASS; these are software-only, not HX/servo physical validation.
pip check and git diff check PASS. Windows Flutter analyze clean,30 tests and
REAL release build PASS. Existing canonical JS client14 tests PASS on Windows
Node24; no Node install or Python inference replacement was introduced on Jetson.

## Deployment and rollback

Current artifact: `.native-build/flutter/scheduled_worker_20261026_r1`.
Primary Flutter source: D:/DA_KT_NC/feeder_demo; checkout snapshot frontend/feeder_demo.
API40-flutter-real.conf selects this reviewed artifact. Stop the worker by setting
its enabled environment to0 and restarting the existing API; sensors/AI remain
separate services. A full rollback to the older preview-only frontend must also
restore its compatible backend sources and drop-in from this session's backups;
do not point an old strict client at the new API and assume format compatibility.
Keep database/tombstones/receipts; never reset user data or the staged index.
