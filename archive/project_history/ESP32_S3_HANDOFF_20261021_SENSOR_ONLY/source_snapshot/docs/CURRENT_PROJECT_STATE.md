# CURRENT PROJECT STATE — for_cat — 2026-10-21

## Canonical current decision (supersedes all historical checkpoints below)

**Production vision remains C++14/OpenCV/CUDA/TensorRT FP16 on Jetson Nano 2GB.**
USB webcam -> YOLOv8n -> CAT / DOG / NONE. One black cat is the main subject;
OWNER_CAT/OTHER_CAT is future/legacy, never a prerequisite for current integration.
The user confirms the detector runs smoothly and physically recognizes CAT/DOG.
This is owner-reported real operation, not a new physical test performed in this audit.

- Production source: `/home/toan/for_cat/jetson/ai/cat_dog_trt.cpp`.
- Existing engine: `/home/toan/for_cat/models/tensorrt/yolov8n_320_fp16.engine`.
- No production detector/model/engine changes in this update.
- Current assembly: ESP32-S3,16MB flash,no PSRAM,2 cores,240MHz; DS1302, OLED0x3C.
- Current semantic areas: FOOD_ROI (front-left eating bowl), WATER_ROI (front-right
  drinking bowl). Stainless bowls may share a color. Earlier colored lids/RED
  fixture wording are legacy; colors do not classify behavior. Coordinates remain
  unconfigured until actual final-camera calibration.

## Audit boundary / source divergence

Audited Windows Git mirror on `main`, HEAD `ac17065`, including pre-existing
uncommitted V3 firmware/transport/test changes. Inventory:392 tracked files,
27,203 UTF-8 text lines before this update; inspected firmware, profiles, protocol,
safety, detector, C++ shadow/geometry, backend/storage/analytics and canonical docs.
Before-state diff/inventory retained outside the tree at
`C:\Users\chito\AppData\Local\Temp\opencode\for_cat_hardware_audit_20261021`.
`D:\for_cat` is a separate old non-Git snapshot/data/tooling location, not the
source checkout to overwrite. No reset, commit or push performed.

SSH to `toan@server-jetson.local` failed hostname resolution in this audit.
**Actual Jetson branch/worktree/deployment parity is NOT REVERIFIED.** Last remote
checkpoint was `dff667d` with V2 staged work; local `ac17065` and current changes
must be reconciled against actual remote work before selective synchronization.
Do not blindly `git pull`, reset or overwrite a remote dirty tree.

## What exists versus what is planned

| Component | Source actually found | Current maturity |
|---|---|---|
| CAT/DOG/NONE | `jetson/ai/cat_dog_trt.cpp`, latest-frame C++ runtime | Physically working, owner confirmed; preserved |
| Tracker/ROI/FSM | `jetson/ai/shadow/`, geometry tool, C++14 single-cat IoU/centroid tracker | Standalone software-tested; NOT linked into production camera |
| HX711/DS1302/OLED/ultrasonic | `esp32/include/m4/`, ASCII diagnostics | Drivers/host tests exist; new assembly physical validation pending |
| Current GPIO | `current_hardware.h`, `config/hardware_current.json` | Owner-selected map; sensor-only safe subset configured; no output permission |
| PIR / approach / operational water | Updated current sensor diagnostics, schema2 ASCII reports | Software preparation, not physical PASS |
| Servo / pump | Inert drivers, output compile guard, portable desired-state policies | NO real PWM/MOSFET actuation; no bench arm/driver implemented yet |
| Closed-loop dispense | `safety_logic.h` models net positive weight delta/time/daily gates in SIM | Pulse/close/settle/MAX_PULSES and physical integration still TODO |
| Feed arbiter | Existing `FeedService`, durable IDs/idempotency, real SERIAL feed blocked | Not the future unified AUTO/SCHEDULE/MANUAL arbiter |
| Load-cell EATING trend | Python stable pre/post fusion and C++ temporal foundations exist | Significant-trend single-cat C++ adapter/FSM still TODO |
| Serial | Frozen binary v1 + separate bounded ASCII diagnostics/read-only monitor | GET_STATUS alive byte is NOT sensor telemetry; DB/API telemetry bridge TODO |
| SQLite / API | Existing Python FastAPI control-plane source, schema2 repositories | Host-tested; C++ detector bridge and actual Nano backend deployment not verified |
| Web / touchscreen | Old frontend references outside repo | `/kiosk` and `/app` NOT implemented here; one backend/database/API is the target |
| Scheduler | No scheduler implementation or schedule tables found | One-time/daily/weekday/offline sync TODO |
| Preference | Existing experimental identity-dependent arithmetic | Single-cat multi-trial adapter and validated real grams TODO |
| Inventory | Generic calibration primitives | #2 pins TBD; calibrated inventory/alerts/prediction TODO |

Existing Python backend is reported honestly as existing software, not introduced
as a replacement production vision runtime. Modern app code needs Python>=3.10;
Nano system Python3.6 cannot run it as-is. Python bring-up/tooling remains offline
or explicit diagnostic use. Do not install/upgrade target runtimes automatically.

UARTv1 FEED_REQUEST has an empty payload; it does not carry source/targetgrams/CAT/
distance evidence. `dispatch::Controller::simulated_target_grams=10` is an existing
SIM-only fixture default, not the new40g physical target. Keep that regression
contract; explicit bounded operational protocol/arbiter work is still required.

## Current hardware and evidence

USB camera x1; HX711/load cell x1; PIR x1; HC-SR04 x2; JSN-SR04T V3.0 x2;
servo x1; pump5V/F5305S x1; OLED x1; DS1302 x1; ESP32-S3.
Exact GPIO table, voltage/power and staged commands: `ESP32_S3_SENSOR_STATION.md`.

- HC-SR04 #1: approach12/13, NOT food inventory.
- JSN-SR04T #1: operational water14/15; actual sensor placement/blind-zone/LOW-TARGET
  calibration must validate that it can observe the controlled bowl/level.
- HC-SR04 #2: food hopper inventory, TRIG/ECHO TBD.
- JSN-SR04T #2: water reservoir inventory, TRIG/ECHO TBD.
- GPIO10 optional water input remains reserved/unconfirmed, not assumed installed.
- Servo6/pump7 known wiring declarations; active safe firmware still leaves their
  GPIO untouched. Old button12/buzzer13 assignments are removed from current profile.
- Prior UART/OLED/RTC/HX711 bring-up is owner-reported historical evidence, not PASS
  for the reconfigured whole system. Installation of HX711 in the new assembled
  rig is unconfirmed (`installed:null`), not permanently asserted NOT_INSTALLED.

Distinguish **SOFTWARE PASS**, **HOST TEST PASS**, **COMPILE PASS** from
**PHYSICALLY WIRED**, **PHYSICAL NOT TESTED**, **PHYSICAL PASS**. Only explicit
measurement/output evidence can award physical PASS; build/report parsing cannot.

## Current implementation direction

1. **Feed:** fresh confirmed CAT + valid stable calibrated HC-SR04 #1 near evidence
   + session/daily/cooldown/interlocks -> unified request -> ESP32 final authority.
   DOG/NONE/stale/ambiguous evidence never produces CAT auto feed.
2. **Target is about40g ADDED**, not total bowl weight. Capture stable
   `weight_before_dispense`; bounded pulse -> CLOSE -> settle -> stable reading;
   `dispensed_grams=stable_after-weight_before_dispense`. No angle/time=grams.
   Require pulse/time/grams limits, HX health, not-busy, durable duplicate/session
   protection, daily caps, reset recovery and fail-safe close. These are roadmap
   requirements, not already working physical functions.
3. **EATING does not require a newly trained NN now:** CAT near FOOD_ROI + filtered,
   significant sustained negative weight trend, noise threshold/minimum duration/
   hysteresis. Close after cat leaves and a stable valid reading is obtained.
   Never interpret tiny oscillations as eating. Missing final stability -> incomplete
   event/null consumption, not invented grams. Dispensing/refill/tare/calibration
   changes, spill/contact/lift invalidate or qualify attribution.
4. **Water:** operational LOW/TARGET evidence + ESP32 validity/hysteresis/timeouts/
   cooldown/dry-run protection -> pump. DRINKING never triggers pump. Inventory
   reservoir level is not automatically evidence that the drinking bowl needs water.
5. **App:** one backend, one SQLite database, one REST API, one responsive Web:
   `/kiosk` local touchscreen and `/app` phone/admin. AUTO/SCHEDULE/MANUAL share one
   arbiter. Internet loss is different from Jetson loss: local kiosk needs no Internet;
   ESP32 schedule fallback still needs explicit revisioned sync, DS1302 validation
   and duplicate-ownership/reboot tests. No raw public port exposure planned.
6. **Analytics:** multiple comparable trials of grams/ratio/latency/duration/returns/
   refusal; no neural LIKE/DISLIKE, no fixed one-meal preference conclusion.
   Inventory percentages only after actual full/empty geometry calibration; tapering
   hopper surface-height percentage is not automatically a mass/volume percentage.
   Days-remaining requires enough valid history/calibrated quantity. Future anomaly
   alerts describe unusual behavior, never diagnose illness.

## Existing Windows video/training evidence (not production)

22 actual MP4 sources,3,063 retained frames at `D:\for_cat\video_cat_review_v1`.
Assistant-authorized pilot V6 has165 selected frames:64 EATING/33 DRINKING/68 IDLE,
no confidently selected food_2 EATING. No fake HUMAN_REVIEWED marker; base archive
labels remain unset. A real Windows CPU frozen-YOLOv8n linear probe was trained
outside this repo at `D:\for_cat\runs\behavior_pilot_20261021_trial01`:
train54/validation59/test52 by day, validation42/59, test13/52 (25%). It is NOT
production-ready or integrated into TensorRT/C++ and is not a required next gate.
Video is optional evidence for validating the sensor-fusion rule, not a prerequisite
to build the scale/servo flow. Retain old data and training artifacts.

## Next task / verification

**Next single physical test: isolated HX711 food-bowl calibration and repeatable
known-mass add/remove test, with servo/pump power disconnected.** Use `diag_hx711`,
which explicitly opts into the scale and uses current4/5. Preserve the raw serial
transcript/reference masses; no automatic tolerance/PASS is invented.
Implementation order and acceptance gates: `ROADMAP.md`.
Current-run software/compile logs and manifests are in the dated audit evidence;
historical counts below are not claims for the new pin mapping.

### Executed current-source checks

Final `checks_final/summary.json`: **378 Python PASS**,140 native safety +3351
driver assertions,6 actual-firmware-loop cases/142assertions/22decodedreports,
26 bidirectional process E2E cases,7 UARTgoldenvectors,40 compileguards,
**21/21 PlatformIO profiles COMPILE PASS**. Native fuzz2000iterations/12000assertions,
Pythonparserfuzz1000iterations; iterations are not separate named tests.
UBSan runtime canary VERIFIED and native/firmware-loop/process/fuzz checks PASS
under `--sanitize undefined`. ASan not claimed: existing Windows runtime probe
was unavailable/unverified. Host C++14 shadow rebuilt/tested:250,028 checks PASS;
this is not a new Nano TensorRT build or physical behavior validation.

Durable handoff: `D:\for_cat\ESP32_S3_HANDOFF_20261021_SENSOR_ONLY` (sensor-only
`diag_hx711` bundle, source snapshot, logs/manifests, NOT_TESTED physical report).
Full logs original location:
`C:\Users\chito\AppData\Local\Temp\opencode\for_cat_hardware_audit_20261021\checks_final`.
Ruff/diff whitespace checks PASS. No serial device available from Windows device
enumeration; no serial open/MCUflash/actuation performed. Repository-default dataset
checker reports absent data only in its default path, not the external Windowscorpus.

## Historical pre-2026-10-21 single-cat checkpoint — STALE for current wiring/priority

**Current physical configuration (user declaration, not measured PASS):** one
black cat; FOOD bowl/lid YELLOW/ORANGE; WATER bowl/lid BLUE. Load cell/HX711 is
NOT INSTALLED in the feeding setup; grams/consumed_grams remain unavailable.
`config/hardware_current.json` is the machine-readable declaration. Older RED
food ROI wording/fixtures below are historical design assumptions, not current
bowl identity or physical validation. Production CAT/DOG runtime is unchanged.

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
