# Flutter REAL frontend — local Jetson demo

## Live views

- `http://192.168.137.59:8000/kiosk` — MANUAL/KIOSK.
- `http://192.168.137.59:8000/app` — MANUAL/APP, mobile web layout.
- `http://192.168.137.59:8000/diagnostics` — previous dark diagnostic UI.

Reload once to replace an already-open old diagnostic page with Flutter.
Subsequent state and request updates do not need manual reload. A phone/laptop
must reach this Jetson LAN address. The Cloudflare reference stays unchanged;
HTTPS public pages cannot directly consume private HTTP/ws merely through CORS.

Same backend/port, canonical SQLite, one existing serial C++ bridge, unchanged
C++ TensorRT detector/passive state tap. No second camera or serial reader.
Legacy transport/camera/AI `MOCK` environment settings on the API unit disable
the older competing pipeline; canonical `SYSTEM_STATE_PROVIDER=REAL` reads the
actual bridge/AI cache and does not substitute mock data.

## State and controls

REAL is the compile-time default. `FEEDER_MODE=mock` is explicit development
only and labelled MOCK. Optional `FEEDER_API_BASE_URL` supports development;
normally URI origin supplies REST and WS endpoints. Path selects KIOSK or APP.

REST bootstrap `/api/status`; bounded WS reconnect `/api/ws/state`; unavailable
data becomes UNKNOWN/null, never fixed percentages or cached healthy numbers.
The three-second client watchdog hides stale state. Inventory #2 is NOT_WIRED;
HX grams remain null, calibration DEFERRED. Sensor NOT_CONFIGURED/null is an
honest current observation, not grounds to replace it with historical readings.

The feed button opens an explicit confirmation. It sends only a MANUAL35g
preview to `/api/feed/preview` through the existing C++ arbiter. A random ID is
stored before POST; lock/short-intent guard prevents duplicate intents. Uncertain
errors retain the ID; retry uses it again; pending reload resumes GET-only.
Receipts are checked for source/sub-source/35g, blocked status, no actual grams,
and actuator_execution=false. History labels these events DRY RUN, not completed
food. 35g means future actual added mass, not current bowl total or servo time.

## Startup after a Jetson reboot

User services remain **disabled for boot autostart**, as before. With the devices
connected, use the existing services (no additional process instances):

```sh
systemctl --user start for-cat-esp32-bridge.service for-cat-ai.service for-cat-api.service
systemctl --user status for-cat-esp32-bridge.service for-cat-ai.service for-cat-api.service
```

The unchanged AI runner waits for a free enumerated camera. The C++ bridge owns
USB serial. The API's additive user drop-in is
`~/.config/systemd/user/for-cat-api.service.d/40-flutter-real.conf`:

```ini
[Service]
Environment=FORCAT_FLUTTER_WEB_DIR=/home/toan/for_cat/.native-build/flutter/real_20261025_v2
```

Serving assets does not re-enable the volatile ultrasonic Echo acknowledgments
after an ESP32 reboot. Existing sensor-only acquisition workflow remains separate.

Latest acquisition check (14:32Z25Oct): the existing fixed-command helper restored
both Echo ACKs. HC/JSN now reach both Flutter views as actual cm or null according
to canonical validity, verified against WS frames. HC read6.57–6.91cm in the
browser window. JSN intermittently read~24cm,285–314cm or null and its timeout
counter advanced130->137. This is an observed raw ranging quality problem,
not a Flutter fabricated/cached value and not stable water accuracy certification.
Review a perpendicular flat target clearly outside the JSN near blind zone
(e.g.40–50cm, subject to the actual module's specification), beam clearance and
physical geometry before considering thresholds. No near/water threshold or
actuator operation was enabled. Evidence:
`evidence/sensor_resume_20261025T142603972574Z/browser_verified.json`.

Follow-up20s capture after user-reported40–50cm target placement:21 distinct
ESP32 reports, JSN11 valid/10 invalid,14 added timeouts, median24.39cm and
range23.53–42.39cm. Current stability is NOT PASS. The simultaneous HC sample
was21/21 valid with no added timeout. Inspect actual JSN target/probe/module
arrangement before any software masking or operational water threshold work.
See the `jsn_target_40_50cm_20261025T145526538248Z/capture.json` subdirectory in
the same sensor_resume evidence folder;192 WS frames are not192 measurements.

## Source and rebuild

Primary user source: `D:/DA_KT_NC/feeder_demo`.
Reviewable source snapshot: `frontend/feeder_demo` in this Jetson checkout.
Original source/build backup and REAL archive/manifest:
`D:/for_cat/FLUTTER_REAL_INTEGRATION_20261025`.

On the Windows Flutter SDK (currently `D:/dev/flutter/bin/flutter.bat`):

```text
flutter pub get --offline
flutter analyze --no-pub
flutter test --no-pub
flutter build web --release --no-pub --no-wasm-dry-run --no-web-resources-cdn --base-href=/flutter/ --dart-define=FEEDER_MODE=real --output=<new-release-directory>
```

Use a new reviewed release directory, not the original published `build/web`.
Keep local CanvasKit/fonts and correct base href. After confirming REAL build
flags/tests, package `forcat_build.json` next to index.html with at least:

```json
{"mode":"REAL","base_href":"/flutter/","target_grams":35}
```

The installed marker also records timestamp and source SHA256 fingerprints.
This marker is operator build metadata, not a signature or an independent
proof of compile flags. Backend startup rejects incomplete assets, MOCK marker,
wrong base href/target or missing local CanvasKit before opening its database.
Deploy the reviewed directory, verify SHA256, point the existing API drop-in
at it, then daemon-reload/restart ONLY the API. No Flutter SDK or new backend
is installed on Jetson. Hardware pin/firmware/AI changes are not needed.

To return to the previous dark views, remove only the owned
`40-flutter-real.conf` drop-in and daemon-reload/restart the API. Keep backups
and data. `/diagnostics` also remains available without changing configuration.

## Verification and evidence

`evidence/flutter_real_20261025T101559672983Z/` contains:

- Backend345 PASS, compile/diff logs; original modified backend files, Git
  staged/unstaged diffs, initial index and protected AI hashes.
- Flutter source/asset SHA256 deployment manifest; source snapshot and reviewed
  REAL artifact. Flutter analyze NO ISSUES,16 Flutter tests and release build
  were run on Windows. Do not describe these as Flutter runs on Jetson.
- Actual Chromium112 screenshots/semantics/network at the LAN origin, desktop
  kiosk800px and app430px. HX raw changed with the same navigation time origin.
- API SIGSTOP/CONT simulation: stale numbers hidden, no mock fallback, restored
  without page refresh. This is software availability testing, not cable unplug.
- Each view: confirmation double-click produced one POST, one inbox row, one
  C++ arbiter event; expected UNATTENDED_SAFE_MODE/WEIGHT_NOT_CALIBRATED.
  Actual grams null, actuator execution false, feeding tables stayed0/0/0.
- All observed assets local, no external URLs or runtime/network errors in the
  successful browser run. Browser test processes were stopped afterwards.

The first complete backend run had an existing bridge absent-device exit test
time out at5s. Its standalone recheck passed in1.26s; a complete rerun passed345.
No test was skipped or its timeout weakened. Startup-null-DOM, merged semantics
label and transient-dialog harness mistakes were corrected; unsuccessful
attempt logs remain separate. Flutter transport lost-response/reload behavior
is provider-unit-tested, not claimed as browser fault-injection proof.

No physical dispensing/servo/pump/gram accuracy test was performed. Existing
GPIO21 diagnostic PHYSICAL PASS and earlier sensor confirmations are preserved.
