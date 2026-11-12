# CURRENT project state — forr_cat

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
