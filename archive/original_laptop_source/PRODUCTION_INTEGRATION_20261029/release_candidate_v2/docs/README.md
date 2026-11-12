# FOR_CAT release_candidate_v2 — post Phase4, supervised deployment preparation

This is a NEW immutable source release, not the obsolete overnight release_camera.
No ARM64/CUDA/TensorRT/runtime/network/physical PASS is claimed by packaging.
Source and static web are the qualified Phase1–4 versions. The engine stays at
`/home/toan/for_cat/models/tensorrt/yolov8n_320_fp16.engine`, outside this release.

## 1. First Windows transfer command (owner runs later)

From PowerShell, after verifying `toan@server-jetson` resolves to the intended Nano
and the target inbox does not already exist:

```powershell
scp -r "D:\for_cat\PRODUCTION_INTEGRATION_20261029\release_candidate_v2" toan@server-jetson:/home/toan/forcat-inbox-rc-v2
```

This copies the directory to `/home/toan/forcat-inbox-rc-v2` when that path is NEW.
It does not merge into `/home/toan/for_cat`. Compare `manifest.sha256` via a trusted
channel. Manifest digests are integrity checks, not signatures/authentication.
Never transfer over an existing inbox or use the old release_camera bundle.

## 2. Exact first Jetson command: READ-ONLY preflight

```sh
/home/toan/for_cat/.venv/jetson-integration/bin/python -B /home/toan/forcat-inbox-rc-v2/tools/control.py preflight --release /home/toan/forcat-inbox-rc-v2 --production-root /home/toan/for_cat
```

Use Python3.11 integration venv, NOT Ubuntu18.04 systemPython3.6. Preflight reads
architecture/compiler/OpenCV/json-c/sqlite3/CUDA/TRT headers+libraries, engine
hash, Python package imports, live user units, camera owner/permissions, memory,
disk and DB columns/user_version. It never opens `/dev/video0` or `/dev/ttyACM0`,
starts inference, changes services/env/network or writes production SQLite/NVS.
User services are inspected with `systemctl --user`, not the system manager.
Only safe known env keys are returned; private configs are not printed.

Minimums: aarch64, Python>=3.11, Python SQLite>=3.24 (UPSERT), pydantic2/FastAPI,
OpenCV4, json-c/sqlite3 development pkg-config, g++C++14, CUDA runtime/headers,
TensorRT headers/libnvinfer, writable external staging, >=512MiB free disk and
>=256MiB MemAvailable as a starting floor (not a sufficient Nano benchmark).
Ubuntu18.04 system SQLite can be3.22: if integrationPython links3.22, STOP and
review its environment; no OS/package install/upgrade is performed by tools.

The expected engine SHA is historical evidence. A mismatch is a STOP for owner
review, not permission to replace/rebuild the engine. The fixed engine path in
the preserved detector must agree with production-root. Full TensorRT ABI and
engine bindings are checked only by the compiled probe after legacy AI is stopped.

## 3. Stage, private config and ARM64 build (all commands default DRY_RUN)

Set these shell variables for subsequent commands:

```sh
PY=/home/toan/for_cat/.venv/jetson-integration/bin/python
IN=/home/toan/forcat-inbox-rc-v2
REL=/home/toan/forcat-staging/releases/release_candidate_v2
BUILD=/home/toan/forcat-staging/build/release_candidate_v2/run1
PRIVATE=/home/toan/forcat-private-rc-v2
BACKUP=/home/toan/forcat-backups/rc-v2-before-cutover
```

Plan staging, then owner repeats with explicit apply/confirmation:

```sh
"$PY" -B "$IN/tools/control.py" stage --release "$IN" --output "$REL"
# Owner reviewed NEW external target:
"$PY" -B "$IN/tools/control.py" stage --release "$IN" --output "$REL" --apply --confirm STAGE_RC_V2
"$PY" -B "$REL/tools/control.py" integrity --release "$REL"
```

Prepare only NEW private files, outside release and production. Replace actual
lowercase hostname and login. This release deliberately starts VIEW_CAMERA-only:
FEED_MANUAL and CONTROL_SYSTEM are not granted by its config generator.

```sh
"$PY" -B "$REL/tools/control.py" configure --release "$REL" --output "$PRIVATE" --hostname ACTUAL_LOWERCASE_HOST.ts.net --viewer ACTUAL_VIEWER_LOGIN
# After review, same command + --apply --confirm PREPARE_PRIVATE_RC_V2
```

Files runtime.json/access.json/producer.token0600, folder0700. The secret stays
server-side. Fixed candidate providers remain SYSTEM_STATE_PROVIDER=REAL,
CAMERA_PROVIDER=MOCK, AI_RUNTIME=MOCK, ESP32_TRANSPORT=MOCK, AI_SHADOW_MODE=true.
Streaming REAL is the independent C++ read-only path; provider modes are not
silently switched. Worker disabled; bridge integration stays enabled/read-only.
Candidate settings do not edit production .env. No Tailscale command is applied.

```sh
"$PY" -B "$REL/tools/control.py" build --release "$REL" --output "$BUILD"
# Owner reviewed preflight/resources:
"$PY" -B "$REL/tools/control.py" build --release "$REL" --output "$BUILD" --apply --confirm BUILD_RC_V2
```

Native C++14 compiles roi_ai_source, esp32_bridge, legacy ai_state_tap and
engine_probe into a NEW directory outside release/production. It records logs,
preflight and binary hashes. It does NOT execute them or automatically deploy.
Only the existing bridge remains running; the newly built bridge is NOT installed
or started by this release's cutover. No firmware/parser changes are included.

## 4. Backup before ANY production write

```sh
"$PY" -B "$REL/tools/control.py" backup --release "$REL" --output "$BACKUP"
# Owner checks target path and current user unit inventory:
"$PY" -B "$REL/tools/control.py" backup --release "$REL" --output "$BACKUP" --apply --confirm BACKUP_RC_V2
```

Backup uses SQLite backup API from a read-only source connection, not raw copy
of a live WAL database. Destination integrity_check must be ok; backup includes
user-unit fragments/drop-ins, prior90-forcat-rc-v2.conf if present, service active
states and protected detector/supervisor/engine hashes. Private receipts/files
are checksummed. Copy the completed private backup off-device through a trusted
owner channel before cutover if durable recovery is required. Never put it in
Flutter or a public release. Backup failure forbids cutover.

Schema strategy: no destructive migration, DROP/ALTER/DELETE or DB replacement.
`schema/contract.json` records required names/types/PK from the packaged API;
existing conflicts fail preflight/cutover. Missing tables are additive CREATE IF
NOT EXISTS by the existing app/adapter. `additive_reference.sql` is reference,
NOT an auto-run migration. Extra NOT NULL/no-default columns block writes and are
explicitly rejected. Keep existing SQLite/WAL/history/NVS data.

## 5. Controlled camera/API cutover — OWNER MAINTENANCE WINDOW ONLY

Known blocker: `/dev/ttyACM0` firmware is HX711_REFERENCE; current bridge expects
diag_current_hardware; valid telemetry=0. Do not flash or broaden the parser.
Only a read-only camera/API rollout may be considered now, with the explicit
`--ack-telemetry-blocker` flag. Feeding/physical system acceptance remains BLOCKED.

Review current service lifecycle hooks. Unknown/nonempty ExecStartPre/Post or
ExecStop/Post, changed units since backup, schema conflicts, incompatible engine,
busy camera/cache-writer, missing private config/build/backup or uncertain owner
identity are STOP conditions. Resolve by owner review, never auto-force/killall.

```sh
"$PY" -B "$REL/tools/control.py" cutover --release "$REL" --build "$BUILD" --private "$PRIVATE" --backup "$BACKUP" --python "$PY" --ack-telemetry-blocker
# OWNER explicitly authorizes a maintenance window; then repeat +:
# --apply --confirm CUTOVER_CAMERA_API_ONLY
```

The controlled script:
1. Verifies immutable release/native artifacts/private config/successful backup.
2. Stops API then AI using systemctl --user, which stops the old supervisor as
   a service rather than killing one child that the supervisor could recreate.
3. Requires both units stopped, fuser camera-free and canonical AI-writer lock free.
4. Runs the target engine/ABI probe (NO camera/inference) only while AI is stopped.
   Probe checks runtime/header major, deserialization, explicit batch/linear FLOAT32
   input1x3x320x320 and output1x84x2100; internalFP16 allowed, COCO CAT15/DOG16.
5. Uses target systemd-analyze to verify generated concrete config, installs ONLY
   the two checksummed90-forcat-rc-v2.conf drop-ins, reloads user manager and checks
   effective ExecStart. Base units, bridge, detector binary and engine are untouched.
6. Starts API then candidateAI. No Tailscale change or health/rollback auto-chain.

New lifecycle: candidate supervisor starts compatible StateTap writer first,
requires readiness AFTER canonical lock + initial DB commit, THEN starts producer.
Producer owns one Capture/inference and its capture lock. Framed records and
preview share epoch/frame/capture time. Diagnostics stay stderr; state stdout
bounded. Either child exiting stops its peer; systemd restarts the whole pipeline
with backoff5s/start limit5per60s. KillMode=control-group prevents orphan captures.
The legacy C++tap remains in the old unit for rollback; it never runs beside the
new writer. No additional inference/runtime is started by the API.

Cutover failure leaves services stopped/partially applied and a journal in backup;
it does NOT automatically rollback, hide failure or retry around STOP criteria.
Owner chooses explicit rollback below. New camera initially OFFLINE/CONNECTING;
new epoch requires new decoded JPEG, never old-frame LIVE.

## 6. GET-only post-deploy verification and private HTTPS

After a few seconds of warm-up/demand, owner explicitly verifies:

```sh
"$PY" -B "$REL/tools/control.py" verify --release "$REL" --private "$PRIVATE"
# Same + --apply --confirm VERIFY_READ_ONLY to issue bounded GETs
```

Local verification uses trusted loopback identity headers to test the application
contract. It is NOT proof of Tailscale authentication/remote reachability. It GETs
health, canonical systemstate, camera/status?watch=true and mjpeg?frames=1 with
response/time limits, plus an unauthenticated403 check. No feed/manual POST,
producer upload or UART is sent. Camera/API contract can PASS while overall system
remains BLOCKED_ESP32_TELEMETRY. Status is reported, never promoted to physicalPASS.
On FAIL, stop owner acceptance; do not claim a successful production deployment.

Private Tailscale Serve HTTPS must be reviewed/configured by owner separately,
after backing up its existing mappings. Read-only commands: `tailscale status`,
`tailscale serve status --json`; check that Funnel is absent and no existing route
will be overwritten. Proposed mapping, NOT run by these tools:
`tailscale serve --bg --https=443 http://127.0.0.1:8000`.
Never use Funnel/router public port, disable authentication or bindAPI0.0.0.0.

Browser on LAN+tailnet: `https://ACTUAL_HOST.ts.net/flutter/`; same origin forAPI,
status andMJPEG. Test Xem/Tắt, LIVE/CONNECTING/OFFLINE/ERROR, up to4viewers, fifth429,
lease expiry/reconnect and unauthorized identity403. REAL/SIMULATED labels must
match provenance; never overlay polled oldAI boxes on JPEG. VIEW_CAMERA cannot
control/manual feed; producer token is not a viewer/control credential.
Repeat on phone with Wi-FiOFF/4G+Tailscale only after LAN PASS. Owner may run:

```sh
"$PY" -B "$REL/tools/control.py" verify --release "$REL" --private "$PRIVATE" --remote --apply --confirm VERIFY_READ_ONLY
```

Remote command uses real HTTPS with normal certificate checks, no forged Serve
headers, GET-only. Tailnet/session/LAN/4G verification requires actual owner logs.
Auth is per new request; existing MJPEG has bounded300s lease, not an immediate
midstream Tailscale session revocation service. SystemStateWS uses current
handshake authorization; no new application auth/session mechanism is invented.

## 7. Exact explicit rollback

```sh
"$PY" -B "$REL/tools/control.py" rollback --release "$REL" --backup "$BACKUP"
# OWNER confirms restore of previous TWO user units, then same command +:
# --apply --confirm RESTORE_PREVIOUS_USER_UNITS
```

Rollback verifies the private backup and our journal, rejects owner edits to
overrides, stops API/AI, checks camera/writer free, restores only prior drop-ins
(or removes ONLY the exact verified new drop-in if previously absent), daemon-
reloads the user manager, and restarts only units that were active before backup.
It does NOT restart bridge, change engine/binaries/network or replace SQLite.
Check `systemctl --user is-active` for3units, old supervisor ExecStart and one
camera owner. Oldtap accepts its legacy detector stdout; old cache reader ignores
extra JSON fields until legacytap writes its next snapshot. Feed remains locked.

The consistent DB snapshot is disaster-recovery evidence, NOT automatically
restored during service rollback (that would lose later owner records). If a DB
restore is ever necessary, STOP and inventory all writers including bridge, close
them under owner supervision, preserve current DB+WAL+SHM together, verify backup
integrity and plan a dedicated atomic offline restore; never copy a backup over a
running WAL DB or delete sidecars blindly. No destructive migration was performed
by this release, so normal rollback keeps the live DB.

## 8. Acceptance labels

Staging-ready means source/package/scripts/offline evidence ready for the owner,
NOT target binary or production success. ARM64_TENSORRT_BUILD_PASS,
JETSON_REAL_CAMERA_PASS, TAILSCALE_REMOTE_PASS, ESP32_TELEMETRY_PASS,
HX711_PHYSICAL_PASS and ACTUATOR_PHYSICAL_PASS remain NOT_VERIFIED until separate
real logs/review. Servo/pump remain LOCKED. No additional milestone is started.

## 9. Release notes and focused test plan

RCv2 includes the actual post-Phase4 framed producer/StateTap, shared epoch/frame
identity, provenance/freshness, stdout/preview backpressure, FastAPI reader fixes
and Flutter REAL/MOCK source-generation/HTTPS fixes. It includes current app web
fallback assets as well as both qualified Flutter builds. No old release_camera
file is selected as a deployment source. Original detector/geometry dependencies
are preserved source includes, not an overwrite of the running detector binary.

New deployment engineering is limited to immutable integrity, read-only preflight,
selected CUDA toolkit path, isolated native build, managed writer-readiness/peer
cleanup, user-unit drop-ins, consistent backup, explicit cutover/verification and
rollback. Lifecycle hooks/owner edits are fail-closed rather than cleared blindly.
Python SQLite>=3.24 and pydantic>=2 are explicit preflight gates; no package
installation or host environment repair occurs automatically.

Offline qualification checks exact source/Phase4 web hashes and groupsA–J,
manifest path escapes/tampering, every write action defaultDRY_RUN, confirmation/
Linux gates, unit templates/Python syntax, C++14 package include compilation,
fresh bundled Python imports, real LOCAL SQLite adapter/cache/schema integration,
fake systemd stop/probe/start ordering, busy-camera/ABI-failure STOP conditions,
backup corruption and owner-edit rejection, exact restore of prior overrides,
writer-ready-before-producer and peer cleanup. All systemd/camera actions in these
tests are fakes; native binaries are Windows portable test executables only.

Target acceptance is separate: read-only preflight -> staged ARM64 build -> private
config -> verified backup -> supervised cutover/probe -> GET-only checks -> LAN
browser -> tailnet4G. Preserve stdout/stderr/build/probe/verification logs with
manifest and binary hashes. A failed check stops acceptance and requires an owner
decision, not automatic cutover retries/rollback. ESP32 reference-mode telemetry,
HX mounting and every actuator remain separately NOT_VERIFIED throughout.
