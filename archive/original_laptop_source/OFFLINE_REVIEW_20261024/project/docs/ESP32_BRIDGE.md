# ForCat REAL integration — Jetson C++ / USB / SystemState

Implemented and tested on the real `/home/toan/for_cat` Jetson Nano2GB, Ubuntu18.04,
aarch64, during2026-10-23. Latest execution evidence:
`evidence/overnight_integration_20261023/`. Physical validation declarations remain
separate from live availability and software tests.

## Single ownership / single backend

```text
ESP32-S3 -> USB Serial -> C++ esp32_bridge (only continuous serial owner)
                        -> canonical jetson/data/events.db
Existing camera -> existing C++ TensorRT cat_dog_trt -> C++ ai_state_tap -> same DB
                        -> RealHardwareProvider -> ONE SystemState
                        -> existing FastAPI backend -> REST + WebSocket
                        -> /kiosk and /app (same responsive page/state)
```

No ESP32 Wi-Fi, MQTT, cloud, second backend, second database, Python inference or
browser serial access was added. The legacy binary UARTv1 transport and mocks are
preserved for development/regression, not run alongside the C++ serial owner.
`ESP32_BRIDGE_ENABLED=1` refuses legacy `ESP32_TRANSPORT=SERIAL` and blocks the old
manual-feed endpoint before it creates a feed record or sends anything.

The pre-existing real repository had no usable `/kiosk` or `/app` frontend files.
Thin shared views were added, not an existing frontend overwritten. Prior mock
sources are `jetson/app/serial_link/mock_transport.py`, `app/camera/mock_camera.py`,
`app/ai/interfaces.py`, `app/simulator/` and explicit demo/test fixtures. Those
remain intact. `SYSTEM_STATE_PROVIDER=REAL` is the web default; explicit `MOCK`
selects a labelled development provider. REAL never falls back to numeric mocks.
Legacy Python camera/AI MOCK configuration in the service keeps that inactive
observation subsystem from competing with the real C++ camera owner; web AI values
come exclusively from the existing TensorRT process.

## Live endpoints and startup

- `http://localhost:8000/kiosk`, `http://localhost:8000/app` on Jetson.
- LAN: `http://192.168.123.18:8000/kiosk` or `/app` (current discovered LAN address).
- `GET /api/status`: coherent REAL SystemState; initial state for both views.
- `WS /api/ws/state`: bounded2Hz state publication, max8 clients, newest-only
  queue1/client, bounded send timeout, same-origin browser check.
- Existing `GET /api/v1/status` retains the legacy shape and adds actual
  `esp32_telemetry`, `system_state` and real AI state in integration mode.
- `GET /api/v1/esp32/status`, `/api/v1/esp32/events`: detailed read-only status/history.
- `POST /api/feed/preview`, `GET /api/feed/preview/{request_id}`: **dry-run inbox**,
  not dispensing. Only MANUAL KIOSK/APP is exposed publicly; trusted AUTO/SCHEDULED
  producers use the same C++ arbiter. The Feed Now control remains disabled.

The backend listens on IPv4 LAN/local interfaces, not a public Internet deployment.
No router/firewall/port-forward/cloud access was configured. All assets are local.

```sh
systemctl --user status for-cat-esp32-bridge.service for-cat-api.service for-cat-ai.service
curl --fail http://127.0.0.1:8000/api/status
```

Three tested user units are installed under `~/.config/systemd/user/` and started;
they remain **disabled for automatic boot**, and no lingering configuration was
changed. Stop/start deliberately with `systemctl --user stop/start UNIT`. Do not
open another serial monitor while the bridge owns the tty. API queries never open
the port. Device discovery checks actual sysfs USB ancestry and refuses ambiguous
multiple boards. `--device PATH`, `--usb-serial SERIAL`, `--baud`, stale/reconnect
settings are explicit overrides; default baud115200, no guessed tty path.

## Actual device / truthful availability

Initially ESP32 was absent from USB enumeration. It subsequently appeared as:

```text
/dev/ttyACM0
/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00
VID:PID 1a86:55d3, serial5C85066678, dialout access already available to toan
```

The running C++ bridge detected it without a Windows COM assumption. Live reports
from `diag_current_hardware` established OLED HEALTHY, PIR transitions, real HX raw
counts and button HIGH/released/count0. Two fixed sensor-only Echo-enable commands
were sent by an exclusive one-time helper after checking safe reports, with the
continuous bridge stopped for that session. No concurrent reader or arbitrary TX
interface was introduced. Divider acknowledgement is prior USER confirmation,
not a voltage measurement. No actuator, calibration/save, reset or flash command
was sent. Serial opening may reset the USB board; Echo confirmations remain
volatile across real board resets.

Live approach was approximately75–77cm with validity=true and NOT_CALIBRATED
wrapper health. Natural sample variation propagated through REST, WebSocket and
rendered DOM without refresh. No deliberate target movement or exact ruler
calibration was performed by the assistant. **Current water reports TIMEOUT/null**;
the earlier owner-confirmed JSN ranging/display result is preserved, but current
unavailable readings are not replaced with demo values or percentages.

Primary web values become null/UNKNOWN/STALE on loss of freshness. Retained bridge
telemetry is labelled history (`telemetry_usable_now=false`), not shown as live.
Freshness uses host monotonic time, host boot identity and progressing ESP uptime;
duplicates/frozen uptime cannot keep a stalled device fresh. Actual USB loss uses
POLLHUP/error and reconnect backoff; split/oversized/malformed JSON recovers.
Duplicate keys, non-finite/type/range errors are rejected. Unsafe arm/AUTO/output
telemetry latches BAD_TELEMETRY and closes the serial port without sending a command.

HX gram calibration stays DEFERRED. The UI exposes real raw counts but grams=null,
calibrated=false; no counts-to-grams conversion exists here. Both inventory#2
sensors stay NOT_WIRED, percent=null, GPIO TBD. GPIO10/16/17/18 remain RESERVED.

## Working AI preserved

Source `jetson/ai/cat_dog_trt.cpp`, binary and TensorRT engine hashes are checked
against the pre-session audit and unchanged. No retraining, TensorRT rebuild or
Python production inference. The existing detector's actual stdout contract
(`ENGINE_CONTRACT=PASS`, CAT15/DOG16, NONE/DETECTIONS lines) is consumed by a separate
C++ tap into `ai_latest` in the same SQLite DB. Missing/stale output becomes
UNKNOWN, never fake NONE/CAT. Live observed classification was NONE; newly
presenting CAT/DOG physically was not part of the unattended verification.

A user-started detector PID9198 already held the camera when a second smoke run
was attempted; that attempt failed opening `/dev/video0`. Its command/cwd/selected
display environment were checkpointed, it was gracefully stopped by SIGINT and
the **same unchanged binary/engine** was run headlessly under the single AI unit
with `--no-snapshot`. No user backup was deleted. State tap failures no longer mask
the producer via shell pipeline status. Transient SQLite cache-write contention
is counted/skipped rather than killing the tap or resetting serial.

## Arbiter / decision software — DRY RUN ONLY

All production-mode execution is blocked. One C++ `FeedArbiter` handles observed
button requests, configured AUTO candidates and the bounded durable dry-run inbox.
Top-level sources are exactly AUTO_CAT/SCHEDULED/MANUAL, manual sub-sources
BUTTON/KIOSK/APP. Request identity, timestamp,35g target, duplicate/capacity checks,
busy, cooldown and safety qualification are represented. Results always contain
actuator_execution=false and actual_dispensed_grams=null. The old production feed
ledger/history is not populated by synthetic or dry-run events.

- **AUTO:** configurable near distance, multiple new samples and sustained time,
  max sample gap; CAT only. DOG/NONE/far/transient/stale/invalid inputs reject.
  **No production near threshold is set**. Default0 means UNCONFIGURED; optional
  `--near-cm`, `--near-stable-ms` are reviewed operator settings, not calibrated defaults.
- **Button:** installed firmware already reports GPIO21 active LOW/pull-up/40ms
  diagnostic counts. Counter increments are one dry-run request; unchanged count,
  initial/reboot baselines and missed gaps are not replayed. User press/hold
  evidence is still required for physical button PASS.
- **Time:** Linux system clock/synchronization and wallclock jump detection feed
  TIME_VALID. Only SCHEDULED requests depend on it. `ScheduledRequestGate` submits
  a deterministic Meal Plan due-instance ID into the shared arbiter inbox, blocks
  invalid time/future/missed-window requests and prevents catch-up bursts.
  Persistent Meal Plan CRUD and an autonomous scheduling worker are **not implemented
  or started by this session**; the adapter and gate are implemented/tested.
- **Behavior:** IDLE -> APPROACHING -> NEAR_FOOD -> EATING -> LEAVING -> IDLE.
  EATING requires calibrated, valid sustained meaningful filtered weight decrease.
  Real gram calibration/noise threshold is absent, so no real EATING/consumed-grams
  claim is made; consumed_grams=null. No EATING neural network was added.
- **Water:** separate sensor-only dry-run LOW/TARGET hysteresis, cooldown, runtime
  cap and invalid-sensor fail-safe OFF. AI has no pump API. Production thresholds
  remain unset; `--water-low-cm` / `--water-target-cm` must be reviewed together.
- **35g:** reuse the existing portable supervised dispense policy with fake HX,
  fake servo and fake journal only. Baseline10 -> after45 yields **ADDED35g** in the
  synthetic test. Pulse/close/settle/stability/fault limits are software preparation,
  not physical dispensing. No calibration means real dispensing remains blocked.

## SQLite / runtime / evidence

Canonical DB remains `jetson/data/events.db`, existing `PRAGMA user_version=2` and
`events`/`typed_records`/`feed_requests` preserved. Online backup precedes live
migration. Additive `esp32_latest`, bounded `esp32_events`(1000 rows), bridge schema
metadata, `ai_latest` and bounded `feed_dry_run_requests`(256, fail closed) use the
same DB. No incompatible replacement DB. JSONL log ring is current +2 rotated
files, roughly1MiB each. Busy writes are bounded/counted; stale cache is not live.

System Python3.6 cannot run the existing modern FastAPI/Pydantic2 application.
A SHA256-verified standalone aarch64 Python3.11.17 and isolated environment were
installed under `.venv/jetson-runtime` and `.venv/jetson-integration`; system Python,
CUDA/OpenCV/TensorRT packages were not replaced. See evidence `runtime.json` for
asset URL/digest and pinned `jetson/requirements-realtime.txt` for runtime/WS deps.

Evidence and reproduction commands:

```sh
sh scripts/build_esp32_bridge.sh
.venv/jetson-integration/bin/python scripts/verify_esp32_integration.py
.venv/jetson-integration/bin/python scripts/run_integration_regressions.py
.venv/jetson-integration/bin/python scripts/verify_live_vertical_slice.py
```

New-process synthetic tests use Linux PTYs and temporary SQLite only. Real browser
proof uses installed Chromium/CDP with real wall time, stored DOM/screenshots and
successive rendered states; an earlier virtual-time dump did not yield usable live
evidence and was not accepted as proof. `vertical_slice/evidence.json` records actual local/LAN
REST, real WS frames, both rendered views and no-refresh updates. A stopped-reader
stale/recovery exercise is explicitly different from a physical USB-unplug test.

## Important source divergence / remaining physical work

**Late-session hardware change:** after the successful full vertical-slice proof,
kernel USB/UVC logs reported camera disconnect/address errors(-71), and the camera
no longer appeared in lsusb or `/dev/video0`. ESP32 later re-enumerated/rebooted;
button count14 and an OLED FAULT were observed, Echo ACKs cleared. Current web
correctly shows AI UNKNOWN/STALE, approach/water null/NOT_CONFIGURED and OLED FAULT.
This does not overwrite earlier owner physical declarations or imply that current
availability is healthy. New AI supervision waits for a character device/free
camera owner, then launches the same binary; it does not power-cycle USB or load
TensorRT repeatedly while the camera is absent. Recovery after actual camera
replug still requires physical verification. Both units remain safe/read-only.

The later `availability_recovery/evidence.json` verifies REAL REST/WS/DOM with
unavailable values and a SIGSTOP/SIGCONT receiver-only stale/recovery exercise;
no physical USB unplug or controlled target motion was performed by the assistant.
Earlier positive live distance/AI screenshots remain in `vertical_slice/`.

The real repo started on main/dff667d with36 staged user files and a latency backup.
Staged index bytes and protected AI hashes remain unchanged; no reset/clean/pull,
commit or push was done. The staged **legacy ESP32 source still has conflicting
old sensor/button pin roles**. It was preserved rather than blindly overwritten;
no ESP32 image was built/flashed from it. Added portable policy headers/tests are
not a firmware deployment. The current board's diagnostic telemetry is the live
source; review/sync that firmware source separately before any future flash.

User actions still needed: controlled target movement with distance notes to
confirm the whole display chain, physical USB unplug/replug observation, GPIO21
press/hold evidence, JSN target/placement/no-Echo investigation, reference-weight
gram calibration and later separately supervised actuator tests. OLED/PIR need
no repeat physical test unless regression. No sensor accuracy, mechanical closure,
pump flow or35g physical dispensing PASS was awarded overnight.

After a deliberate ESP32 reboot, if the already-reviewed divider wiring is still
correct, the operator can re-enable only sensor acquisition with:

```sh
.venv/jetson-integration/bin/python scripts/enable_verified_sensor_acquisition.py
```

This helper discovers the identified board, stops the continuous reader, checks
safe current-profile reports, sends only the two fixed Echo-confirmation strings,
records a new uniquely named evidence run and resumes the reader. It performs no
flash, calibration/save or actuator command. Do not run a competing monitor.

## Failures encountered and resolved/qualified

- Old Git does not implement `git branch --show-current`; used symbolic-ref.
- System Python3.6 lacks SQLite online backup; the failed empty backup artifact
  was retained and the verified isolated3.11 runtime performed the actual backup.
- `systemd-analyze --user verify` cannot create a manager in this SSH/cgroup
  context. This is not a claimed static-verify PASS; daemon-reload/LoadState and
  actual running-service/API behavior were checked instead.
- First native policy-test build exposed a const-data-member assignment error;
  changed the invariant to static constexpr and compiled/ran the actual tests.
- Camera duplicate ownership, pipeline exit masking, SQLite busy writer death
  and headless verification harness issues are described above and in evidence.
