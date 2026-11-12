# CURRENT project state — forr_cat

## HX711 host calibration SOFTWARE READY / waiting physical TEST0 — 2026-10-26

Owner now has nominal1/2/5/10/20g references; primary fit/validation points are
0/5/10/20/30/35g. SOFTWARE READY only:0 production reference points, no active
coefficients, no PHYSICAL gram PASS. Prepared session
`hxcal_91ca4d57d8c24e5d92a3f063a8b01494`, AWAITING_ZERO. Stop here until the
operator removes reference loads and explicitly runs TEST0; do not advance to
servo/pump. Exact command and all later physical steps: [HX711_HOST_CALIBRATION.md](HX711_HOST_CALIBRATION.md).

Audit: raw is signed24-bit, channelA/gain128 in the prior deployed firmware source
reference. MCU ScaleCalibration uses averaged tare and single-reference factor;
NVS m4-calibration/sensors-v2 stores a39-byte version1/CRC16 shared record. Current
canonical firmware_calibrated=false; actual MCU tare/factor are not exposed and
remain UNKNOWN, not guessed0. Existing C++ bridge deliberately emits gramsnull
with DEFERRED; old SystemState also blocked gram promotion. No NVS readback/write,
serial command or firmware flash was performed for this milestone.

Chosen implementation: host multi-point measurement authority from REAL raw,
separate additive SQLite session/point/active-model tables in the same canonical
events.db. No second serial/camera/backend. Candidate offset is the robust zero
mean; counts_per_gram=sum(mass*raw_delta)/sum(mass^2), grams_per_count reciprocal,
grams=(filtered_raw-offset)*factor. Signed slope is supported. Each physical point
requires >=25 inlier distinct telemetry reports over>=25s (default5s settle+30s
capture). Isolated Hampel/MAD outliers bounded10%; contiguous anomalies, excessive
noise/drift/nonlinearity/coarse resolution fail rather than widening tolerance.

Candidate is NOT active gram authority. Independent second-round0/5/10/20/30/35/0
validation is required before activate; restart after activation plus0/35/0 and
explicit operator confirmation are required for PHYSICAL_PASS. Old failed rounds
are retained; explicit reset-phase starts a new verification round. SHA256 checks,
USB/pin/mode binding and sample freshness fail closed. Unrelated Meal Plan edits
do not change calibration; starting a new tare/calibration invalidates old authority.
MCU NVS/controller qualification remain unchanged; host grams do not enable actual
dispensing, EATING/consumed grams or actuator authorization.

API /api/hx711/status and /api/hx711/calibration are read-only; /api/status and
existing WS weight carry calibrated gram/stability/offset/factor/age diagnostics
when valid. Before activation/candidate/unknown/stale/out-of-range -> gramsnull.
Live measurement uses10 unique reported samples (>=8s), resets on data gaps/reboot,
and labels STABLE/UNSTABLE; no single sample becomes final weight. This uses~1Hz
published raw, not all10/80SPS ADC conversions, and is not a servo control loop.

Provisional strict bench criteria: zero +/-0.1g; other references
+/-max(0.1g,1%reference); spread<=0.2g, sigma<=0.05g, half-window drift<=0.1g.
Capacity/reference certificate is unknown; these are agreement targets against
operator nominal weights, not metrology certification. If real small-mass/noise
response cannot meet them, report BLOCKED/limitation rather than fake PASS.

428 backend tests (29 calibration software cases), full worker regression,
native HX/M4 UBSan3351 assertions, existing fake dispense9/99+9 checks, pip/diff
PASS. Flutter analyze clean/34 tests/release PASS; actual kiosk/app show real raw
and null gram/tare/factor at preparation, no control POST. Missing-telemetry
branch and a typed-map fixture error were fixed before passing. A physical reboot/
network loss during preparation required resuming durable staging; this is not
calibration persistence evidence because no real coefficients existed yet.

Evidence: `evidence/hx711_calibration_20261026T041547966931Z/` with source/DB backup,
audit/source references, tests, readiness screenshots and empty physical metadata.
Physical calibration/verification/restart tests: NOT TESTED. All arm/AUTO flags
false/output0/executionfalse, actual_dispensed_gramsnull, target35g unchanged.
AI hashes and36-file staged index preserved; firmware/C++ controller untouched.


## Autonomous Scheduled Worker — SOFTWARE PASS / DRY RUN PASS — 2026-10-26

The existing FastAPI lifespan now runs one scheduled-dry-run-worker background
task in for-cat-api.service, enabled by its50-scheduled-dry-run.conf drop-in,
poll2s. It reads persisted plans and REAL SystemState, uses Vietnam UTC+7,
TIME_VALID/fresh connection/disarmed checks and the existing ScheduledRequestGate
and C++ arbiter. No new backend/database/serial reader/AI runtime/actuator service.
Preview and worker share the same transactional occurrence submission path.

An additive scheduled_occurrences table records one occurrence per plan/Vietnam
calendar date (each plan has one daily HH:mm slot). Revision is not identity.
Occurrence and canonical dry-run inbox row commit in one BEGIN IMMEDIATE
transaction; interrupted/failed insertion rolls both back. Poll/restart/concurrent
preview replay returns the saved request. Retiming a plan after today's occurrence
does not create a second one that day. Disabled/deleted/future/missed/invalid-clock/
unavailable/unsafe plans do not enqueue. Existing60s/no-catch-up policy is retained.
SQLite user_version2, bounded ledgers and original records are preserved.

Live proof10:20:01+07:00: two enabled test plans at10:20 produced two distinct
SCHEDULED/35g requests automatically, originWORKER, each exactly one inbox row
and C++ feed_request_dry_run event. The disabled same-time plan produced0.
No preview POST occurred before this proof. Request A:
`schedule_7996f4ce027cdc591d2564d57a9e5e8b5dc2356ea5ead400`;
request B: `schedule_692bbd1f02c911c3322da10586cdbff69631bda8db651019`.
Both decisions DRY_RUN_BLOCKED/UNATTENDED_SAFE_MODE/WEIGHT_NOT_CALIBRATED,
actuator_execution=false, actual_dispensed_grams=null. Repeated polling and real
API restart changed worker_id/PID but retained the same2 occurrences/requests/
events; restarted submitted_count0 and duplicate_observations4. A later revision
edit and explicit preview reused the original identity. Test plans were deleted;
only their tombstones/occurrence evidence remain. Real feeding tables stayed0/0/0.

Regression:399 backend tests (30 new worker cases), existing fake dispense UBSan
9 named cases/99 assertions plus9 fake35g checks, pip check and diff check PASS.
Windows Flutter analyze clean,30 tests/build PASS; existing JS client14 tests
PASS against freshly collected canonical files. Actual Chromium kiosk/app show
RUNNING worker and automatic occurrence history, no control POST/runtime/network
errors. First async fixture callback binding and frontend lint issues were fixed
before passing. Journal capture was corrected for old systemd timestamp syntax;
the2 unique creation log lines are saved separately, with the first failed capture.

PHYSICAL NOT TESTED / BLOCKED: no ESP32 flash, no servo/pump/arm/AUTO activation,
no model/source/binary/engine change, no gram calibration or fake physical feeding
completion. All real safety flags remained disarmed/output0.35g is the requested
future actual-added target; HX gram calibration remains DEFERRED.
Worker counters are per API process; durable recent occurrence history survives
restart. Missing worker/network state is UNKNOWN in Flutter rather than cached
healthy state. Individual new plans still default disabled.

Guide: [SCHEDULED_WORKER.md](SCHEDULED_WORKER.md). Evidence:
`evidence/scheduled_worker_20261026T021542321284Z/` with live_worker_verified.json,
live_http_calls.json, creation journal, worker UI screenshots, manifests, DB/source
backups and full regression logs. Preferred app hostname unchanged; artifact now
`.native-build/flutter/scheduled_worker_20261026_r1`. All36 staged index entries
and protected AI hashes preserved.


## LAN/startup recovery and overnight review — 2026-10-26

User screenshot showed ERR_CONNECTION_TIMED_OUT at the old192.168.137.59:8000/app.
PC now192.168.123.15 and the same verified SSH host is Jetson192.168.123.8.
IPv6 link-local recovered access without changing network addressing. Jetson
had rebooted; all3 existing user services were disabled/inactive, Linger=no.
The existing C++ bridge/AI/API were started, then enabled under default.target;
own-user lingering is now YES. No unit ExecStart/hardware mode was changed.
Actual cold reboot was not performed in this task; configuration enabled/active,
symlinks and Linger=yes were verified. Sensor-only helper restored the2 Echo ACKs
after the MCU reset; this remains a deliberate one-time action, not automatic
boot TX. Prior owner divider confirmation is not a voltage measurement.

Preferred LAN URLs: **http://server-jetson.local:8000/app** and **/kiosk**.
Windows HTTP200 at the stable hostname and newIPv4; actual Chromium verified
both Flutter views, REAL same-origin WS, unchanged navigation time origin and
Meal Plan UI. No control POSTs/runtime/network errors. Primary code/artifact
remains the25-test/369-backend-test meal-plan release; no app/model/firmware change.

Overnight observation is INCOMPLETE, not a full8h PASS: last summary28110.011s
(7h48m30s),938 periodic samples,937 API successes,937 ESP32-connected and937
AI-online observations, one connection-refused sample at16:05:10Z during the
documented API deployment restart. Last file still said RUNNING and FINAL.json
is absent. Exact stop cause is unconfirmed; previous-boot persistent journal
was unavailable. HC valid19/937, JSN valid16/937; invalid/null samples are retained
and not relabelled healthy from owner acceptance. No actuation by the watcher.
Original overnight files are preserved. Derived review is in the new recovery
evidence directory rather than rewriting the old summary as completed.

Watcher now handles SIGTERM/SIGINT and writes an INTERRUPTED FINAL.json on a
graceful interruption. Actual Linux checks: normal2s run -> COMPLETED final;
SIGTERM of its own test child -> INTERRUPTED final with signal15, no serial or
actuator access. Abrupt power loss can still prevent a final write; missing-final
captures remain incomplete. The one-off overnight watcher is NOT boot-enabled.
All36 staged files/index and protected AI source/binary/engine unchanged.
All arm/AUTO flags remain false/output0; gram calibration DEFERRED and35g actual
added target unchanged. Run/discovery/rollback guide: [LAN_STARTUP.md](LAN_STARTUP.md).
Evidence: `evidence/network_boot_recovery_20261026T011718847595Z/`.


## Overnight software continuation / Meal Plan preview live — 2026-10-25T16:13:17Z

Owner accepted JSN basic ranging for the real small setup/storage scale of
approximately25cm, citing the limited dorm desk space, and authorized unattended
software work/observation while the hardware stays powered overnight. Record this
as OWNER_ACCEPTED_BASIC_RANGING_FOR_CURRENT_DEMO, not certified45cm accuracy or
water geometry/threshold calibration. Earlier timeout/outlier evidence is retained.
No further user physical action is required for this overnight software milestone.

Persistent Meal Plan CRUD is deployed on the same backend/canonical SQLite and
the preserved Flutter five-tab UI. The Cho ăn tab has add/edit/delete/reload and
explicit SCHEDULED preview: fixed35g, Vietnam UTC+7, weekdays, revision checks,
default disabled. SQLite schema_version2 is retained with one additive table;
bounded32 active plans/256 identities and deletion tombstones prevent stale-create
resurrection. No default meals were invented. There is NO autonomous schedule
worker: enabled means eligible for explicit preview only, not AUTO/actuation.
TIME_VALID, due-instance60s/no missed catch-up, fresh ESP32 and safe state gate
submission through the existing ScheduledRequestGate -> one C++ arbiter inbox.

Checks:24 new backend tests; complete369 backend PASS on actual Jetson. Flutter
analyze NO ISSUES,25 tests PASS and release build PASS on Windows. Actual Jetson
Chromium created a disabled plan using the editor (Vietnamese name retained),
verified PLAN_DISABLED, edited/revision2, verified NOT_DUE before the slot, then
previewed the actual23:13+07:00 due instance. Repeating preview produced the same
request ID, one canonical inbox row and one C++ arbiter event, SCHEDULED/35g,
UNATTENDED_SAFE_MODE/WEIGHT_NOT_CALIBRATED, actual gramsnull/actuatorfalse. Fresh
/app read the persisted kiosk plan; scheduled DRY RUN history label verified;
app deleted the test plan. Active real plans are empty; one test tombstone remains.
Real feeding/history tables stayed0/0/0. No external requests/runtime/network
errors in the successful browser run. A first harness attempt assumed textbox
roles on semantic nodes; corrected to the actual native INPUT nodes. Flutter
fixture UTF8 headers/async timing and formatting issues were corrected before
passing; a Windows console encoding error occurred after an already successful
build, then the final source was checked/built successfully with UTF8 logging.

8-hour passive observation is running as for-cat-overnight-watch-20261025.service,
sample30s, JSONL rotation1MiB x4, bounded summaries and alerts. It reads only the
existing REAL API: no camera/serial/control access. Source scripts/watch_real_overnight.py,
output evidence/overnight_meal_plan_20261025T153748062876Z/watch_8h/. SUMMARY.json
is live; FINAL.json is produced at completion. Do not claim the full8h passed
before that file/status exists. API restart during deployment is an expected
software availability transition, separately visible if a sample coincided.

Latest16:13 state: ESP32 connected/OLED healthy/HX raw available but gramsnull,
AI NONE/ONLINE; both ultrasonic channels currently invalid/null with ACK enabled.
Those live nulls are retained even with owner acceptance of the near-range setup.
All arm/AUTO flags false/output0. New artifact .native-build/flutter/meal_plans_20261025_r1.
Primary source D:/DA_KT_NC/feeder_demo; checkout source frontend/feeder_demo.
All36 staged files/index and protected TensorRT source/binary/engine unchanged;
no firmware/actuator/pin/NVS/calibration/production-threshold changes.
Guide: [MEAL_PLANS.md](MEAL_PLANS.md). Evidence:
`evidence/overnight_meal_plan_20261025T153748062876Z/meal_browser_verified.json`.


## JSN target test NOT STABLE — 2026-10-25T14:55:46Z

User confirmed a flat target placed approximately40–50cm before JSN #1.
A20.002s read-only canonical WS capture received192 frames but counted only
21 distinct ESP32 reports (not192 independent sensor measurements). JSN:
11 valid/10 invalid samples (52.38% valid), timeout counter966->980 (+14),
valid range23.5298–42.394798cm, median24.3873cm, standard deviation5.1825cm.
Only one sample was near42.39cm; this does not support stable measurement of
the user-reported target position. HC simultaneously had21/21 valid samples,
3.6015–3.6358cm, timeout counter104->104 (+0). No new control/serial command,
firmware change, calibration or production threshold. All captured safety
flags remained disabled. User placement is reported, not independently
measured certified reference geometry. Prior raw-ranging confirmation is not
revoked, but current JSN stability is NOT PASS. Next evidence needed is a clear
photo of the JSN probe/target arrangement and module wiring before changing
firmware or using sensor-based operational water thresholds.
Capture: `evidence/sensor_resume_20261025T142603972574Z/jsn_target_40_50cm_20261025T145526538248Z/capture.json`.


## Sensor-only acquisition restored / Flutter verified — 2026-10-25T14:32:36Z

After a real USB absence, ESP32 and camera re-enumerated at14:25Z; existing
bridge/AI services recovered automatically. Initial14:26 REAL state was safe,
but both volatile Echo ACKs were false. The existing approved helper stopped
the bridge, exclusively opened the previously identified ESP32, checked safe
continuous telemetry and sent exactly `echo-approach-3v3 CONFIRM` and
`echo-water-3v3 CONFIRM`, then restored the bridge as sole serial owner.
Both ACKs remained true after normal bridge ownership resumed. No actuator
command, firmware/pin/NVS/calibration/threshold or application code change.

Six REST samples and8 WebSocket frames verified current REAL/safe/null-gram
state. Actual Chromium112 then matched HC/JSN displayed readings and health
against the canonical WS frames on both Flutter /kiosk and /app without page
refresh, no POST/control submission and no external requests/runtime errors.
Browser samples: HC6.57–6.91cm, valid, timeout count0. JSN showed23.67–24.34cm,
but also285.26/313.76cm outliers and invalid/null samples, with timeout counter
130->137 across browser observation. This proves the data path, NOT stable
water ranging/accuracy. Physical target placement/geometry must be reviewed
before using operational water thresholds; no filter hides these observations.
Earlier REST also observed284.62cm, confirming the issue is upstream of Flutter.

Raw helper uptime restarted during this acquisition window; exact cause was
not isolated. ACKs were explicitly verified afterwards rather than assuming
they survive a reboot. Existing physical validation history remains separate
from this current quality observation. HX gram calibration stays DEFERRED;
35g ACTUAL DISPENSED is still a future closed-loop target, no dispensing PASS.
All arm/AUTO flags false and actuator outputs0 throughout captured reports.

Evidence: `evidence/sensor_resume_20261025T142603972574Z/` including USB/kernel
checkpoint, realtime_verified.json, browser_verified.json and screenshots.
Fixed-command receipt/raw telemetry is linked from realtime_verified.json
under `evidence/overnight_integration_20261023/sensor_enable_...`.


## Flutter REAL frontend deployed and browser verified — 2026-10-25T10:25:48Z

The user's original Flutter orange/blue five-tab UI is now the REAL frontend
at `/kiosk` and `/app`, on the existing Jetson backend and canonical SQLite.
Primary editable source: `D:/DA_KT_NC/feeder_demo`; reviewable source snapshot
in this checkout: `frontend/feeder_demo`. Original Windows source and published
build are backed up under `D:/for_cat/FLUTTER_REAL_INTEGRATION_20261025`.
The public pages.dev reference has not been redeployed. The earlier audit
section below describes the PRE-migration source, not the current provider.

Default mode is REAL: REST `/api/status` + WS `/api/ws/state`, no mock fallback.
Explicit MOCK remains development-only. No fixed percentages, 40g success or
meal counts in REAL. All requests remain MANUAL 35g DRY RUN, KIOSK or APP,
using the existing preview API / one C++ arbiter. Actuator execution is false,
actual dispensed grams null. Gram calibration remains DEFERRED.

Checks: Flutter analyze NO ISSUES;16 Flutter tests PASS; release build PASS.
Real Jetson backend345 tests PASS. First full run had one existing absent-device
bridge exit test exceed its5s timeout; it passed alone in1.26s and the complete
345-test run then passed. The initial failure log is retained, not suppressed.
Actual Chromium112 verified both views at LAN origin192.168.137.59:8000,
live HX raw updates without refresh, API SIGSTOP/CONT -> stale values hidden
-> recovery without refresh, and confirmation double-click -> one POST / one
inbox row / one arbiter event for each KIOSK/APP. Both decisions were
UNATTENDED_SAFE_MODE / WEIGHT_NOT_CALIBRATED. Real feeding tables stayed0/0/0.
All observed font/CanvasKit/API requests were same-origin; no runtime/network
errors or external asset requests in the successful run. Harness startup/DOM
and transient-dialog timing failures are retained separately in evidence.
Lost-response same-ID retry and pending-reload GET-only behavior are covered
by Flutter provider tests; this is not a claim of Flutter browser fault injection.

Live sample10:25:48Z: ESP32 CONNECTED, OLED HEALTHY, HX raw-668040/gramsnull,
AI NONE/ONLINE, button released/count0 in this boot. HC/JSN are currently
NOT_CONFIGURED/null after volatile Echo acknowledgments cleared; no enable
command was sent during this frontend task. Prior ranging/button physical
validation is retained, not replaced with assumed live values. No new physical
accuracy/dispensing certification. All arm/AUTO flags false, output enable0.

All3 existing user services are active, still NOT boot-enabled. Only an additive
API drop-in selects the reviewed REAL artifact under
`.native-build/flutter/real_20261025_v2`. Old dark diagnostics remain `/diagnostics`.
Original36-file staged index and protected AI source/binary/engine unchanged.
No ESP32 flash, NVS/pin changes, new backend, actuator or production AI changes.
Run/rebuild/rollback details: [FLUTTER_FRONTEND.md](FLUTTER_FRONTEND.md).
Evidence: `evidence/flutter_real_20261025T101559672983Z/flutter_browser_verified.json`
and screenshots, deployment manifest, backend regression logs/original backups.


## User frontend located — 20261025T093212874924Z

The user identified the existing Flutter UI at D:/DA_KT_NC/feeder_demo,
published reference https://bua-an-cua-meo.pages.dev/. This is the UI to
preserve for next integration. It is outside this Jetson checkout.
main.dart directly instantiates MockFeederBackend; current lib has no
HTTP/WS client. Fake percentages94/75/82, meal counts and900ms success40g
must not leak into REAL. Source audit in an isolated copy found2 errors
and1 warning; originals unchanged. Migration is audited/planned, not
implemented. Keep mock as explicit development mode; add REAL provider
using the existing SystemState /api/status and /api/ws/state plus
preview request API,35g target, unknown/null semantics and blocked acts.
Prefer same-origin local/LAN Flutter assets served by this backend;
HTTPS Cloudflare cannot simply fetch private HTTP/ws endpoints. No
public port forwarding/ESP32 Wi-Fi/new backend is required. Existing
dark Jetson pages are diagnostic views, not a replacement design for
the user Flutter app. Evidence: `evidence/existing_flutter_frontend_20261025T093212874924Z/frontend_reference.json`.


## User kiosk preview request verified — 20261025T091234683206Z

User supplied a real MANUAL/KIOSK preview result. Request ID `manual_kiosk_33dda9390029a2a75053f5d72e94bd1a`
was read back from the API and exists once in canonical SQLite. Target35g,
DRY_RUN_BLOCKED / UNATTENDED_SAFE_MODE / WEIGHT_NOT_CALIBRATED,
qualified=false, actuator_execution=false and actual_dispensed_grams=null
are the expected current result. This verifies user-operated kiosk
request delivery through the arbiter, not physical dispensing.
Evidence: `evidence/kiosk_user_preview_20261025T091234683206Z/receipt.json`.


## Feed Now web DRY RUN live verified — 2026-10-25T09:03:24.422477+00:00

Both /kiosk and /app now use the shared Feed Now — DRY RUN request client and
existing preview API / one C++ arbiter / canonical SQLite. REAL fresh safe
state enables diagnostic submission only. MANUAL sub-source is KIOSK or APP;
target35g, actuator_execution=false and actual_dispensed_grams=null. The old
real feed endpoint remains blocked. No camera/species or TIME_VALID gate is
imposed on MANUAL preview. Public scheduling/AUTO producers remain separate.

Client persists one random request ID BEFORE POST, locks while in flight,
guards fast double-clicks, polls with bounds, keeps ID after uncertain errors
and restores pending intent with GET only after reload. Realtime loss disables
new intents. It never reports a completed feed from a dry-run decision.

Actual Jetson regression:340 Python tests PASS. Client unit tests:14 PASS on
Windows Node24.19.0 (not a claimed Node run on Jetson). Actual Jetson Chromium
verified kiosk double-click -> one inbox row/arbiter event; app lost response
after real server commit -> same-ID POST retry -> one row/event. Both show
UNATTENDED_SAFE_MODE / WEIGHT_NOT_CALIBRATED. Real feed/history tables did not
change. UI test requests are explicitly diagnostic, not feeding events.

A real-browser native timer Illegal invocation was found before any POST,
fixed with correctly bound global timer wrappers and regression-tested. The
initial fault-injection browser harness did not intercept the bound client
fetch; its normal APP request completed safely. The harness was corrected
to inject only a client transport response loss, then same-ID recovery was
verified. Initial failure evidence remains in the earlier session directory.

No firmware/pin/partition/NVS/model/engine/actuator change. GPIO21 diagnostic
PHYSICAL PASS and gram calibration DEFERRED remain distinct. User should
refresh once to load the new asset; later request results update in-page.
Evidence: `evidence/feed_now_dry_run_20261025T084809753339Z/browser_verified.json`.


## GPIO21 diagnostic PHYSICAL PASS / latency fix — 2026-10-25T04:34:47.817066+00:00

User confirmed short presses now respond quickly and each produces exactly
one request. A continuous5s hold produces no repeat; release adds no request.
Together with real LOW/HIGH screenshots/telemetry, GPIO21 basic diagnostic
input/debounce/press-edge/one-shot validation is PHYSICAL PASS. This is not
servo/feeding validation. All requests remain dry-run/blocked by the arbiter;
target35g ACTUAL DISPENSED and gram calibration DEFERRED are unchanged.

The reported3–5s display delay had a reproduced software contributor: the
bridge logged press events without publishing their state immediately, and
its1Hz publisher could expose JSON1.4–2s old. Jetson now publishes on new
JSON/accepted press events and WS polls100ms. Observations carry raw/stable
levels, device timestamp and TELEMETRY/PRESS_EVENT provenance. Press events
do not refresh the age of other sensors. Release still relies on the
firmware1Hz JSON stream and may take roughly one report period to appear.
Firmware debounce remains40ms; NO ESP32 source/flash/pin/actuator change.
Actual Jetson C++ build and339 tests PASS; original failing regression was
reproduced first with synthetic PTYs, then passed on the candidate. The
user separately confirmed the real quick-press and5s-hold behavior. The
passive20s retest monitor saw released/count59, not the hold itself; the
hold-duration sign-off is explicitly USER evidence.
Evidence: `evidence/button_latency_fix_20261025T032950396111Z/final_user_validation.json`.


## GPIO21 user evidence review — 2026-10-25T03:02Z

User images show PRESSED/LOW count45 then RELEASED/HIGH count45. Canonical
history confirms one request45 at03:02:10Z, LOW/count45 at03:02:13Z, HIGH/
count45 at03:02:18Z and no added request through03:02:44Z. Minimum observed
debounced LOW interval is2225ms; exact continuous3–5s hold
duration and one-press correspondence still require the user
confirmation. Full button PHYSICAL PASS is not awarded from two still
images alone. The real request reached the shared arbiter with35g target,
actual_dispensed_grams=null and WEIGHT_NOT_CALIBRATED/UNATTENDED_SAFE_MODE;
actuator_execution=false. Evidence: `evidence/button_hold_review_20261025T030420984593Z/review.json`.


## User kiosk evidence — 2026-10-25T02:54:57Z

User screenshot proves real sensor values reached kiosk: APPROACH3.81cm
valid=true and WATER_OPERATIONAL25.90cm valid=true; both NOT_CALIBRATED
labels are expected wrapper status, not ranging failure. OLED HEALTHY,
HX raw-675245/grams=null, PIR transitions10, button released HIGH with
diagnostic request count4, AI NONE/ONLINE and actuator-blocked banner.
These are rounded displayed readings, not independent ruler references.
No production near/water threshold or full button hold/debounce physical
PASS is inferred. Later API samples are recorded separately and may
return null when Echo is unavailable; do not substitute the screenshot
numbers as live data. Evidence: `evidence/ultrasonic_kiosk_user_image_20261025T025833884875Z/verification.json`.


## Owner camera/AI test confirmation — 2026-10-25T02:51:18.609953+00:00

The user confirmed the camera/AI integration test was OK after the camera
reconnect and live REST/WebSocket verification. Record: USER_CONFIRMED_TEST_OK.
Exact tested classes and kiosk/app route were not specified, so no new
per-class accuracy result is inferred. Canonical record: `evidence/camera_ai_owner_confirmation_20261025T025118609990Z/confirmation.json`.


## Camera return verified — 20261025T024203157510Z

User reconnected USB camera4a54:5233; /dev/video0 is owned by the existing
unchanged TensorRT detector under for-cat-ai.service. REAL REST and six
WebSocket frames show AI ONLINE with advancing timestamps; classification
observed: NONE. ESP32 remains connected and all arm/AUTO/output flags
are disabled. No process restart, source/model change, flash or actuator
command was required. This resolves the previous camera-unavailable
observation, not a new physical CAT/DOG accuracy certification.
Evidence: `evidence/camera_return_20261025T024203157510Z/camera_live_verified.json`.


## Resume / verified offline update — 2026-10-25

SSH/IP is now192.168.137.59. The six-file offline cache/availability patch was
checksum-compared, applied with backups, and verified on real Jetson Python3.11:
**336 tests PASS**, py_compile/pip check/diff check PASS. The staged Git index and
protected TensorRT source/binary/engine are unchanged. No firmware flash/NVS or
actuator command. Current links: http://192.168.137.59:8000/kiosk and /app.

Captured REAL REST/WS/Chromium proof: ESP32 /dev/ttyACM0 connected, OLED HEALTHY,
PIR configured, HX raw available and grams=null/calibration DEFERRED, button HIGH/
count0 at capture. Both Echo channels were re-enabled with fixed sensor-only
commands after safe telemetry checks, but currently report TIMEOUT/null; no fake
distance is substituted. Camera is not USB-enumerated, so AI is UNKNOWN and its
service waits for hardware. Public observed behavior is UNKNOWN while AI is
unavailable, with the controller's internal state separate. Clock is TIME_VALID;
all physical feeding/water execution remains blocked, no production near/water
threshold is configured and35g ACTUAL DISPENSED remains the canonical target.

Both /kiosk and /app rendered REAL state and updated without manual refresh.
Evidence: `evidence/resume_offline_20261025T022048133690Z/` including runtime_verified.json,
DOM/screenshots, linux_backend_all.log and package comparison/receipt.
Historical availability reports below retain their original timestamps.


## Latest real integration — 2026-10-23 (supersedes older checkpoints below)

**Late-session availability change (16:09–16:13 UTC):** the camera disappeared
from USB enumeration (`error -71`, `/dev/video0` absent), so current AI is correctly
UNKNOWN/STALE, not fake NONE. ESP32 remains connected with real HX/PIR/button data;
its later reboot cleared Echo ACKs and OLED now reports FAULT. Button count14 was
observed, but full press/hold physical PASS is not inferred. The successful earlier
camera+approach+REST+WS+Chromium evidence is retained in `vertical_slice/`; later
truthful unknown/null views and stopped-reader stale/recovery are separately
recorded in `availability_recovery/`. Camera service now waits for hardware rather
than repeatedly loading TensorRT when the camera is absent. Physical cable/power
and OLED regression review are required; no flash/power-cycle was performed here.

The REAL Jetson `/home/toan/for_cat` now runs one C++ USB serial owner, one shared
SQLite database, the existing backend, coherent REAL SystemState, REST/WebSocket,
and working `/kiosk` + `/app` views. Actual device `/dev/ttyACM0`, USB1a86:55d3,
serial5C85066678. Live sensor data and existing C++ TensorRT AI output reached both
Chromium-rendered views and updated without refresh. REAL never substitutes mock
numbers; missing/stale data becomes null/UNKNOWN/STALE. Exact implementation,
tests, evidence, startup and limitations: **[ESP32_BRIDGE.md](ESP32_BRIDGE.md)**.

Canonical hardware declarations/pins: `config/hardware_current.json`.
OLED0x3C/PIR11/HX raw/HC#1 raw ranging retain PHYSICAL PASS; JSN#1 ranging/OLED
display is user-confirmed working, but the current live water reading is timeout/
null. Button21 diagnostic is present and consumed; actual press/hold PHYSICAL PASS
is still pending. Gram calibration DEFERRED awaiting1/2/5/10/20g weights; primary
reference20+10+5=35g. Target **35g ACTUAL DISPENSED**, never servo time or bowl-total.
DS1302 remains out of required scope; Jetson time is canonical. Inventory#2 NOT
WIRED, GPIO TBD; GPIO10/16/17/18 RESERVED.

All feed/water execution remains blocked: arm/AUTO flags false, actuator output0
in real telemetry, no servo/pump command sent. Configurable AUTO temporal gate,
shared dry-run arbiter/inbox, scheduled TIME_VALID due-instance adapter, behavior
FSM and water fail-safe preview are software-only; production near/water thresholds
unset. No real EATING/consumed grams or35g dispense claimed. No autonomous scheduler
or actuator service was started. User units are running but not boot-enabled.

Protected AI source/binary/engine and the original36-file staged Git index are
unchanged. The staged ESP32 source is still the older conflicting pin map and was
not flashed or blindly overwritten; new portable dispense-policy files are only
compiled with fake IO. Initial work and SQLite were checkpointed under
`evidence/overnight_integration_20261023/`. No commit/push/reset/clean performed.

The previous checkpoints below are retained verbatim as user work/history.

## Current single-cat implementation — supersedes the historical M2 table below

ESP32-S3 offline integration V2: real diagnostic setup/loop now runs with host
Arduino/Wire/NVS/GPIO adapters and the actual Jetson report parser. Six cases,
131 C++ assertions and21 decoded reports PASS, including target ASan/UBSan/LSan.
Found/fixed unsaved HX711 factor loss/stale factor revival when editing level
geometry: successful tare/calibration now synchronize the in-memory record.
Full release remains365 Python /19 firmware profiles /140 safety+3351 driver
assertions /34 guards PASS. No board/serial port or actuator was used. Current
handoff is `ESP32_S3_HANDOFF_20261018_V2`; see `ESP32_S3_OFFLINE_VALIDATION.md`.

ESP32-S3 sensor integration source prepared: documented16MB/no-PSRAM bridge
profile, restored DS1302 support and agreed candidate pins, plus `diag_all_sensors`
for HX711/RTC/OLED/button/alternating levels and a read-only Jetson ASCII monitor.
Software checks:365 final Python PASS,140 safety+3351 driver assertions,34 compile
guards,19 safe firmware builds. Servo/pump remain disabled. No MCU upload or actual
sensor validation was performed; source synchronization status is separate from
build PASS. See `ESP32_S3_SENSOR_STATION.md` for pins, calibration and bring-up.

ROI calibration and geometry-validation tooling is now available in a separate
C++14 executable: original-frame capture, GUI/headless ROI marking, compatible
candidate JSON plus hash-bound dimensional provenance, overlay, MP4/native detector
replay, geometry-only logs/metrics and bounded review images. See
`GEOMETRY_CAMERA_VALIDATION.md` for exact commands and scope. New checks:13 named
native cases /40,044 assertions /40,000 stress iterations,17 named CLI cases,
ASan/UBSan PASS; TSan PASS for pure helpers. Real engine/new-adapter smoke passed
on5 generated MP4 frames. No real fixed-camera MP4 or /dev/video0 was available;
real ROI/geometry validation and GUI/live-camera validation are NOT claimed.
Production source/binary/engine and existing shadow foundation remain unchanged.

Standalone C++14 shadow foundation is implemented: single-cat IoU/centroid
association, bounded bbox history/TTL, strict normalized ROI config, geometry,
timestamped behavior input, elapsed-time smoothing/FSM and paired START/END events.
Actual Nano: **250,028 native checks PASS**, ASan/UBSan/leak detection and TSan
PASS; four synthetic JSONL events and unconfigured-template rejection PASS.
It is not linked into the production detector. No behavior model or live animal
accuracy is claimed. See `CPP_BEHAVIOR_SHADOW.md` for architecture, exact commands,
contracts, evidence locations and limitations. Weights remain null; no history/API
migration or actuator path was added. Existing full Python suite remains344 PASS.

Dataset-workflow host validation: **344 Python tests PASS**, preserving all 317
previous cases and adding 27 video/annotation/readiness cases. Fixtures are generated
MP4/noise data, not real cat ground truth. Real-video availability/readiness must be
reported from the operator's staged inputs; no real import result is inferred from tests.

Dataset workflow update: directory import now preserves original names/full hashes,
media properties and optional non-trainable preference metadata. Extraction defaults
to 2 FPS with source frame/timestamp/sequence and quality flags. Human time intervals
support transition uncertainty and explicit whole-session correction with preimages.
Safe reruns preserve annotations. Source/pair-group splitting and full-budget
JSON/Markdown readiness gates are documented in `BEHAVIOR_V2_VIDEO_WORKFLOW.md`.
User now reports many real MP4s on Windows; none is inferred to be entirely EATING.
No real import is claimed until files are staged/provided. RED=FOOD, BLUE=WATER;
food variants initially change across sessions at the same RED ROI, not a second food
bowl in WATER_ROI. Validated C++ binary/engine and ESP32/UART/safety are untouched.

- One cat only; production AI remains C++/OpenCV/TensorRT/CUDA. No required OWNER/OTHER classifier for Behavior V2.
- Actual Nano validation executed over SSH: original source/binary reconciled, original rebuild matched binary hash, existing engine preserved.
- Latest-frame runtime installed after candidate compile, 30-second headless/snapshot/X11 comparisons, binding checks, offline CAT/DOG/person regression and clean shutdown tests.
- Headless: ~30 FPS. X11: sequential 18.144 FPS / latest 20.077 FPS; driver-buffer timestamp age 254.662 -> 105.464 ms, p95 284.965 -> 122.188 ms. TRT CUDA-event stream span ~21.8 ms in both X11 runs, not an isolated kernel-compute metric. This is not sensor-exposure/glass-to-glass latency.
- One application slot; two V4L2 driver buffers selected after one-buffer capture measured only 15 FPS. Default requests MJPG 640x480 @30, logs actual readback. Camera thread is sole reader in latest mode.
- Live empty scene observed as NONE. Live physical CAT/DOG/PERSON presentation NOT_TESTED_PHYSICALLY; real-engine offline existing-photo regression passed CAT=0.927363, DOG=0.879974, person-photo=NONE.
- Original backup: `jetson/ai/cat_dog_trt.backup_pre_latency`. Existing source `.bak_latency` was preserved. See `JETSON_CAMERA_LATENCY_RESULT.md` for hashes and measured results.
- Behavior V2 schema/tools ready: `schema_version=2`, `subject_label=CAT`, EATING/DRINKING/IDLE, legacy identity field null. NONE/UNKNOWN/UNSURE are not silently IDLE or classifier-usable. Legacy enums/history remain unchanged.
- Existing import/extract/dedup/session split/release/interchange tools reused. Full host suite: **317 Python PASS** (301 existing +16 V2 cases). New C++ capture/contract tests: 27 checks +20,000 publications PASS; same tests passed ThreadSanitizer and ASan/UBSan on Nano. Six decoder/preprocess unit cases PASS. These are scoped software checks, not animal accuracy or sensor calibration.
- `ai/label_schema.py` missing from GitHub baseline was restored from verified legacy contracts plus V2 additions; Nano Python3.6 `bringup.camera` dry-run now passes with camera_opened=false.
- User reports three real ~2-minute videos. No supplied clip found/imported in the repository raw/videos inputs during this session; no behavior training or external dataset download performed.
- RED bowl=FOOD_ROI; BLUE bowl=WATER_ROI; BLUE floor line=approach reference. `jetson/ai/roi_config.example.json` stays unconfigured with null ROIs. Standalone native tracker/ROI/temporal/event implementation exists; production/model/persistence integration remains future work.
- HX711/RTC/water/servo/pump firmware was not changed or flashed. This camera validation confers no new physical sensor/actuator PASS.
- `AI_SHADOW_MODE=true`, `automatic_feed_authorized=false`, `ACTUATOR_OUTPUTS_ENABLED=0` and equivalent gates remain unchanged. No DRINKING->pump or AI->physical-feed path exists.

Next single task: stage one actual fixed-camera MP4/original frame, mark/review RED food and BLUE water ROIs and run the isolated geometry validator. Real-video import/annotation remains pending operator staging; no model training until data validation and explicit authorization.

## Historical pre-hardware checkpoint — retained for chronology

**Primary human-readable source of truth. Milestone: M2 — PRE-HARDWARE SOFTWARE CANDIDATE.** Normal USB webcam → Jetson Nano → USB serial → ESP32-S3 N16R8 candidate → sensors/UI/future servo/pump; existing Flutter/Web ↔ REST ↔ Jetson. Exact seller board, memory, pins and USB route are unverified. AI runs on Jetson; ESP32-S3 is final local actuator safety authority. Canonical diagram: `REFERENCE_ARCHITECTURE.md` / `SYSTEM_BLOCK_DIAGRAM.md`.

Verified current host baseline: **301 Python PASS,3271 native assertions PASS (140 safety +3131 driver),UART7/7,guards18/18,builds11/11**. Actual quality rerun timestamp2026-10-05T08:47:23.028710+00:00; `PRE_HARDWARE_RELEASE_CANDIDATE.md` / `PRE_HARDWARE_FINAL_BASELINE.md`, `.checks/summary.json` and `.release/quality_summary.json` record scope/results. The prior217/1328 handoff was the legitimate starting checkpoint; changes are risk tests/defect corrections, not product features. A PASS below applies only to the named layer. N/A is not a physical PASS; Python modules are host-tested/imported, not MCU-compiled.

| Subsystem | Implemented | Host verified | Simulation verified | Compile verified | Hardware verified | Real-data verified | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Jetson backend | Yes, software | Yes, Windows | Mock/injected | N/A Python | NO | NO | Actual Nano OS/runtime pending |
| REST API | Yes | Yes | Mock lifecycle | N/A | NO deployment | NO | Local default; frontend/auth/TLS pending |
| SQLite | Yes | Yes, reopen/fault/ledger | Synthetic records | N/A | NO target/power-loss | NO | No real animal history claimed |
| Camera abstraction | Yes | Yes | Mock/fake providers | N/A | NO target webcam | NO | Explicit camera choice; no auto capture |
| Video replay | Yes | Yes, generated codec fixtures | Synthetic replay | N/A | N/A file path | NO cat video | Fixture decoding is not animal evidence |
| AI orchestration | Yes, injected interfaces/service | Yes | Supplied test predictions | N/A | NO Jetson runtime | NO | No real model executor validated |
| Temporal behavior | Yes | Yes | Eating/drinking fixtures | N/A | NO | NO | Single active temporal subject |
| Feeding/drinking history | Yes, typed/projections | Yes | Synthetic | N/A | NO | NO | Outcomes and observations distinguished |
| Preference analytics | Yes, experimental | Yes, arithmetic/filters | Synthetic only | N/A | NO weights | NO trials | BEHAVIORAL PREFERENCE TREND, not certainty |
| UART | Yes, frozen v1 | Yes,7 vectors/fake ports | Twin | Yes firmware | NO physical link | N/A | GET_STATUS is not sensor readiness |
| ESP32 safety | Yes, portable policies/gates | Yes | Twin/desired flags | Yes | NO rig | NO measurements | Output permissions hard disabled |
| ESP32-S3 firmware | Yes, safe/diagnostic profiles | Native portions only | SIM explicitly | Yes, surrogate | NO upload/runtime | NO | Seller N16R8 candidate, not identified board |
| HX711 | Yes, driver/math | Yes, fake pin I/O | Synthetic counts | Yes diagnostics | NO | NO calibration | Factor absent until explicit measured calibration |
| RTC/DS3231 | Yes, read/set/validation | Yes, fake bus | Synthetic dates/faults | Yes diagnostics | NO retention | NO reference time | Invalid RTC denies timed feed |
| Ultrasonic core | Yes, bounded/filter/range | Yes, fake edges | Synthetic | Yes diagnostics | NO timing/voltage | NO distances | Polling accuracy unverified |
| Food sensor/level | Yes, separate geometry | Yes | Synthetic | Yes diagnostics | NO | NO full/empty | Invalid/uncalibrated percent absent |
| Water sensor/level | Yes, separate geometry/shadow policy | Yes | Hysteresis/faults | Yes diagnostics | NO | NO levels | would_request_pump never physical ON |
| OLED | Yes, minimal SSD1306 | Yes, fake bus | Status fixtures | Yes diagnostics | NO panel | N/A | Failure non-safety-critical |
| Button | Yes, polarity/pull/debounce | Yes | Press/bounce fixtures | Yes diagnostics | NO wiring | N/A | Intent only; safe build rejects feeding |
| Buzzer | Yes, active-buzzer patterns | Yes | Timed patterns | Yes diagnostics | NO sound/current | N/A | Passive tone generation absent |
| Health/snapshot | Yes, optional/fresh/stale | Yes | Fault fixtures | Yes | NO real evidence | NO | Compile success does not grant HEALTHY |
| Calibration persistence | Yes, codec/adapter preparation | Yes codec | Corrupt/empty records | Yes adapter | NO NVS | NO stored measured calibration | Separate from safety counters |
| Servo | Interface/gates only | Yes rejection | Desired-state twin | Yes, disabled | NO motion/closure | NO | No PWM/angles; output0 |
| Pump | Interface/gates only | Yes rejection | Desired-state twin | Yes, disabled | NO switching/flow | NO | OFF; no active driver |
| Dataset | Tooling yes; real corpus NO | Yes synthetic/video fixtures | Synthetic only | N/A | NO physical capture | NO,0 real samples | DATASET_NOT_AVAILABLE |
| AI/models | Interfaces/config/evaluation yes; trained model NO | Yes tooling only | Supplied fixture arithmetic | N/A target runtime | NO Jetson/TensorRT | NO real predictions | NOT TRAINED; no accuracy/FPS |
| Frontend integration | Existing external project only | NO actual client | API contracts only | Not built here | NO deployment | NO | Old frontend untouched |

Historical PC camera observations are not verification of the required webcam-on-Jetson system. Historical Phase/RC counts and feature gaps remain only in labelled checkpoints; `PROJECT_STATUS_CURRENT.md` is a historical ledger, not this current-state page.

**Safety/configuration:** actuator/servo/pump flags0, final GPIOs unassigned, AI_SHADOW_MODE=true, automatic authorization false, physical SERIAL feed blocked, UART v1 unchanged. **Freeze:** no more pre-hardware features/tests/mock services. Next gates: M3 actual Jetson↔ESP32-S3 USB communication; M4 actual sensors/actuators; M5 actual dataset; M6 actual AI validation. None is passed.
