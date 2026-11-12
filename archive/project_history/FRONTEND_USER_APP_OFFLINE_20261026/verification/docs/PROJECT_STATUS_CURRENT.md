# forr_cat — historical status ledger (not current source of truth)

Historical navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL / NOT CURRENT:** retained checkpoint chronology and old estimates. Current maturity/architecture is `CURRENT_PROJECT_STATE.md` / `REFERENCE_ARCHITECTURE.md`; current verified counts are `PRE_HARDWARE_FINAL_BASELINE.md`; freeze/handoff is `PRE_HARDWARE_HANDOFF.md`. “Current”, “authoritative”, old counts and unimplemented-driver claims below refer to their original checkpoints only. Historical estimates are not a recalculated handoff progress score.

## Historical productization / AI-data readiness checkpoint

- **217 Python PASS /0 failed /0 skipped /0 errors**, unchanged current native **140 safety +1188 driver assertions PASS**, UART**7/7**, guards**18/18**, firmware**11/11**. Full one-command check produced `.checks/summary.json` and logs; no ESP32 driver or UART changes in this pass.
- Added explicit bounded capture/session schema, deterministic sampling/dedup, stronger release/leakage gates, local classification interchange/provenance rejection, candidate/experiment/inactive model registry, supplied frame/event/sweep evaluation, tracking-attribution/report boundaries and report-ready requirements/traceability/FMEA/diagrams/Vietnamese materials.
- **Milestone M2; DATASET_NOT_AVAILABLE; AI NOT TRAINED; hardware NOT VERIFIED; shadow true; actuator flags0; final GPIOs unassigned.** Earlier bring-up work is preserved, frontend untouched. Historical completion estimates are not inflated/recalculated.
- Current release scope, exact verification, boundaries and freeze decision: `PRE_HARDWARE_FINAL_BASELINE.md`; tooling commands: `DATA_CAPTURE_WORKFLOW.md` / `AI_EXPERIMENT_REPRODUCIBILITY.md`; developer map: `SOURCE_TREE_MAP.md`.

## Historical M4 driver preparation checkpoint

- New real-I/O HX711, DS3231, ultrasonic, SSD1306, button and active-buzzer driver paths plus calibration codec/NVS adapter and six explicitly selected safe diagnostic profiles are implemented. Their scope and physical limitations supersede the historical interface-only driver descriptions below.
- **170 Python tests PASS**, **140 safety + 1188 driver native assertions PASS**, unchanged **7/7 UART vectors**, **18/18 compile guards**, **11/11 safe/component firmware builds PASS**. Fake-I/O and PC builds only; no physical sensor, NVS, GPIO, board or actuator validation.
- Milestone stays **M2**, estimates remain **49.64% overall / 66.19% software-preparation**; M3 pack was not recreated. All actuator flags are zero, production/component pins default unassigned, frozen UART v1/frontend unchanged. Normal operational sensing/feeding integration and telemetry negotiation remain future work.
- Results: `M4_PRE_HARDWARE_PREPARATION.md`; component commands and first HX711 workflow: `M4_DIAGNOSTIC_COMMANDS.md`; record: `SENSOR_CALIBRATION_RECORD.md`; wire design only: `UART_SENSOR_STATUS_EXTENSION_PLAN.md`.

## Historical Jetson-side hardening checkpoint

- **163/163 Python tests PASS**, no failures/skips; RC2 125 tests retained. Native C++ **140/140**, UART **7/7**, safe compile guards **5/5**, simulator tests and all four inert firmware regression builds remain PASS; ESP32 source/UART unchanged.
- Jetson preparation adds explicit capture budgets/backends, passive discovery/readiness/storage tools, crop/multi-cat/ROI boundaries, shadow mode, managed observation lifecycle, bounded retries/logging, WAL/atomic storage and failure/clock/soak/concurrency tests. It does not start hardware or validate a real model.
- Synthetic demo/host-overhead benchmark executed, accelerated hour-equivalent soak passed; **NOT JETSON VERIFIED, NOT CAMERA HARDWARE VERIFIED, NOT CUDA VERIFIED, NOT TENSORRT VERIFIED, DATASET NOT AVAILABLE, AI NOT TRAINED**. Shell diagnostics and systemd template are prepared, not installed/run on Jetson.
- Milestone remains **M2**. Previous completion estimates are retained as historical/conservative; no real hardware/data/training/demo credit is added for more host tests. Details and exact benchmark caveats: `JETSON_PRE_HARDWARE_RC.md`.

The RC2 block and original RC1 audit below are preserved historical checkpoints; the hardening update above supersedes their narrower software limitations only.

## Historical RC2 verification record

- Milestone **M2**, not M3. Final RC2 host run: **125 Python tests passed / 0 failed / 0 skipped**, **140 native C++ assertions passed / 0 failed**, **5/5 expected compile guard cases**, unchanged **7/7 UART vectors**. Original 21 simulation definitions still covered. See `PRE_HARDWARE_RC2.md` for exact builds, changes and limits.
- Classic SIM/HW_SAFE plus two **ESP32-S3 compile-surrogate** builds PASS with outputs hard-disabled; candidate seller N16R8 44-pin board remains unidentified. 16 MB flash / qio_opi compile options verified against installed manifests/toolchain/link map; actual 8 MB PSRAM, USB, antenna and GPIOs **not** verified.
- Offline camera → injected predictions → temporal sessions → atomic typed visits → existing Event-shaped API history is now host-tested, including dropout/EOF/model failures and reopen. Default production mocks still UNKNOWN; no identity-based automatic feed. FastAPI does not automatically start a live camera worker.
- Generated MJPG video encode/decode and synthetic session-safe dataset round trip now pass. No webcam opened, real dataset still absent, AI untrained.
- SIM firmware now uses portable command dispatch/policy and emits synthetic final FEED_STATUS; HW_SAFE always rejects physical execution. New CRC/version safety record and host restore tests do not verify NVS hardware. Physical API SERIAL feeds remain blocked.
- **All real hardware, sensor, actuator, cat dataset/trained-AI and final-demo groups stay incomplete.** Existing weighted estimates **49.64% overall / 66.19% software-preparation** are retained as the prior conservative RC1 audit estimate, not automatically increased from more mock tests. No new completion score is manufactured.
- Next physical gate: `ESP32_S3_FIRST_DAY.md` / Jetson environment+Logitech+safe USB link. Remaining real drivers, power/mechanics, measured inference, auth/TLS and old Web/App integration are still required.

**Sections 1–12 below preserve the original RC1 audit checklist/evidence as historical comparison.** Its "not wired/no real video tested" statements refer to RC1; the RC2 changes above supersede those particular software gaps without claiming physical completion.

**Milestone: M2 — Pre-hardware software candidate. Overall completion: 49.64%. Software/pre-hardware completion: 66.19%.** These are checklist-based estimates for the *final real prototype*, not percentages of files written. No source code was modified for this audit. The existing Flutter Web/App is outside this repository; no current architecture uses another MCU/camera board.

## 1. Inventory and boundaries

Final plan: Logitech USB webcam → Jetson Nano (OpenCV, future trained identity/behavior models, temporal fusion, SQLite and REST) → USB serial → ESP32 (sensor, RTC and independent servo/pump safety); existing Web/App ↔ Jetson REST. `README.md`, `docs/ARCHITECTURE.md`, `docs/PRE_HARDWARE_RC1.md`, `esp32/platformio.ini` and `jetson/app/main.py` agree on that design. The *running default* selects `MockCameraProvider` and `MockEsp32Transport`. Selecting SERIAL still rejects manual feed locally; firmware also acknowledges then rejects it. Nothing in this repository enables physical actuator output.

Implemented **software**: FastAPI/status/feed lifecycle (`jetson/app/{main,api/routes}.py`), generic bounded event stores and schema-v2 typed SQLite/ledger (`app/storage/`), Python/C++ UART v1 + golden vectors, pyserial/link manager, camera mock/USB/video providers, host feeding/water policy and 21-case twin, temporal engine/fusion, experimental preference function, UTC daily summary, offline dataset/evaluation tools and safe build/check scripts. These are evidenced by 99 passing Python tests, 101 executed C++ host assertions and two PC firmware builds—not by real Jetson/ESP32/cat outcomes. Current local `jetson/data/events.db` was inspected read-only with `tools.db_maintenance inspect`: schema 2, **0 events, 0 typed records, 0 feed requests**. `ai/datasets/{raw,processed}` and `ai/models` contain only placeholders; `ai.scripts.dataset_report` returns `DATASET_NOT_AVAILABLE`.

## 2. Functional progress matrix

Statuses describe **final-project maturity**, even where a narrower host-only module works. COMPLETE means its explicitly named software/design scope is exercised, never that adjacent real-world behavior is validated.

| ID | Area | Status | Concrete evidence and remaining boundary |
| --- | --- | --- | --- |
| A | Project architecture | COMPLETE | Design only: `README.md`, `docs/ARCHITECTURE.md`, `HARDWARE_TEST_PLAN.md`; physical build absent. |
| B | Jetson FastAPI backend | PARTIAL | `jetson/app/main.py`, `tests/test_api.py`; host tests pass, no Jetson run or camera-inference worker. |
| C | API v1 | PARTIAL | `app/api/routes.py`, `docs/API_V1_CONTRACT.md`, API tests; paths respond in mocks, real behavior ingestion/auth and frontend calls untested. |
| D | SQLite/storage | PARTIAL | `app/storage/{event_store,records,repositories}.py`; tests cover schema migration and bounds; no deployed DB/power-loss proof. |
| E | Event/history | PARTIAL | EventStore + ledger and `tests/test_models_store.py`; PC DB currently empty, vision/drinking typed records not automatically reflected in generic history routes. |
| F | Jetson ↔ ESP32 protocol | COMPLETE | **Wire definition only:** `serial_link/protocol.py`, `esp32/include/uart_v1.h`, `docs/UART_V1_GOLDEN_VECTORS.csv`, Python/C++ tests; physical link untested. |
| G | Link manager/reconnection | PARTIAL | `serial_link/{link_manager,real_transport}.py`, `tests/test_real_transport.py`; fake-port loss/reconnect passes, no USB device. |
| H | ESP32 firmware foundation | FOUNDATION ONLY | `esp32/src/main.cpp`, `platformio.ini`; both builds pass; firmware responds PING/GET_STATUS and rejects all feed requests. No device flashed. |
| I | Feeding safety logic | PARTIAL | `esp32/include/safety_logic.h`, `test/native_safety.cpp` (host assertions); policy is **not called by** `main.cpp` for feeding. |
| J | Water safety logic | PARTIAL | `safety_logic.h`, Python twin + tests; pump state policy is **not ticked by firmware loop** or wired to output. |
| K | Persistent safety state | PARTIAL | `safety_persistence.h`/Preferences adapter and write-ahead policy, host TestStore/reboot tests; real NVS behavior untested, no operational feeding path. |
| L | Sensor driver architecture | FOUNDATION ONLY | `include/sensor_drivers.h` offers health/sample/sim/unvalidated interfaces; no real HX711/ultrasonic driver or calibrated GPIO. |
| M | Servo architecture | FOUNDATION ONLY | `sensor_drivers.h` inert/sim interfaces, `board_config.h` hard output guard; no PWM or mechanical closure driver. |
| N | Pump architecture | FOUNDATION ONLY | inert/sim Pump and water policy in headers; no MOSFET driver, wiring or pump telemetry. |
| O | RTC architecture | FOUNDATION ONLY | clock interface/RTC validity checks (`sensor_drivers.h`, `safety_logic.h`); no live DS3231 driver. |
| P | Camera abstraction | COMPLETE | Software interface and mock `camera/{base,mock_camera}.py`, `tests/test_models_store.py`. |
| Q | USB webcam support | BLOCKED BY HARDWARE | `camera/usb_webcam.py`, `tools/test_webcam.py`; Windows index 0 frame probe passed, **Logitech on Jetson not tested**. |
| R | Video replay | PARTIAL | `camera/video_file.py`, `tools/replay_video.py`, `tests/test_video_file.py`; fake decoder/frames tested, no real saved video replayed in this repo. |
| S | Software simulator | MOCK ONLY | `app/simulator/{controller,transport,persistence,scenarios.json}`, `tests/test_simulator.py`; 21 scenarios use injected identity/weights. |
| T | Dataset import | PARTIAL | `ai/scripts/{import_video,import_capture}.py`, `ai/tests/test_dataset.py`; dry-run and synthetic imports tested, no real video imported. |
| U | Frame extraction | FOUNDATION ONLY | `ai/scripts/extract_frames.py` supports bounded OpenCV decoding; no real video extraction/codec run evidenced. |
| V | Dataset labeling | PARTIAL | `ai/scripts/label_dataset.py`, synthetic test; no cat samples labeled. |
| W | Dataset validation | PARTIAL | `ai/dataset.py`, `validate_dataset.py`, corrupt/synthetic tests; no actual corpus validated. |
| X | Session-safe split | COMPLETE | **Algorithm only:** `ai/dataset.py:split_sessions`, split script and leak tests; no real split exists. |
| Y | Dataset reporting | PARTIAL | `ai/dataset.py:report`, `dataset_report.py`; current output `DATASET_NOT_AVAILABLE`, diversity unassessed. |
| Z | Identity AI pipeline | BLOCKED BY DATASET | `app/ai/{models,interfaces}.py`, `ai/training.py` label map; MockIdentityModel always UNKNOWN, no trained model/inference adapter. |
| AA | Behavior AI pipeline | BLOCKED BY DATASET | `app/ai/interfaces.py`, `behavior/models.py`; MockBehaviorModel always UNKNOWN, no EATING/DRINKING visual classifier. |
| AB | AI evaluation | FOUNDATION ONLY | `ai/evaluation.py`, `ai/scripts/evaluate_predictions.py`; metric arithmetic tested on SYNTHETIC_TEST_DATA, no real predictions/accuracy. |
| AC | Temporal behavior tracking | PARTIAL | `behavior/temporal.py`, synthetic eating/drinking occlusion tests; requires future model predictions/ROI. |
| AD | Eating-session tracking | PARTIAL | `behavior/{temporal,fusion}.py`, typed BehaviorRecord/tests; no real eating time, no automatic camera→DB flow. |
| AE | Drinking-session tracking | PARTIAL | temporal/fusion, typed DrinkingSession/tests; no real drinking observations or water-volume claim. |
| AF | Food consumption estimate | PARTIAL | `behavior/fusion.py:stable_weight/estimate_consumed`; invalid samples return None; load cell uncalibrated/unconnected. |
| AG | Food preference analytics | PARTIAL | `analytics/preference.py`, multi-session synthetic tests, `FOOD_PREFERENCE_EXPERIMENT.md`; zero validated food sessions. |
| AH | Daily behavior summary | PARTIAL | `storage/summary.py`, `/daily-summary`, tests; empty/fixture results work, no animal history. |
| AI | Logging/observability | PARTIAL | `app/observability.py` JSON logs, link stats and `OBSERVABILITY.md`; deployment rotation/monitoring not tested. |
| AJ | Configuration | PARTIAL | `app/config.py`, `.env.example`, pinned requirements, config tests; Jetson-specific paths/packages unverified. |
| AK | Security bounds | PARTIAL | rate/body/key/list/CORS limits (`main.py`, `routes.py`, tests); no authentication/TLS/public-safe network deployment. |
| AL | Old frontend compatibility | PARTIAL | `API_V1_CONTRACT.md`, `OLD_FRONTEND_INTEGRATION.md`; old project schema/browser integration not inspected or tested. |
| AM | Windows dev environment | COMPLETE | `setup_dev_windows.ps1`, `run_checks.ps1`; isolated host suite/native/compiler/PlatformIO run successfully. |
| AN | Jetson deployment preparation | FOUNDATION ONLY | `setup_jetson.sh`, `check_jetson_env.sh`, manual guide; neither script executed on Jetson. |
| AO | Real Jetson validation | BLOCKED BY HARDWARE | No Jetson model/OS/Python/JetPack or on-device test output; `PHASE2_HARDWARE_VALIDATION.md`. |
| AP | Real Logitech webcam validation | BLOCKED BY HARDWARE | No Logitech detected; earlier PC camera was an HP PnP device, not a Jetson test. |
| AQ | Real ESP32 flashing/runtime | BLOCKED BY HARDWARE | `esp32dev_*` PC builds only, no confirmed physical board or upload/runtime log. |
| AR | Real Jetson ↔ ESP32 serial | BLOCKED BY HARDWARE | No `/dev/ttyUSB*`/`ttyACM*`, real PING/GET_STATUS or unplug/reconnect evidence. |
| AS | Real sensors | BLOCKED BY HARDWARE | No HX711, food/water ultrasonic, DS3231, OLED, buzzer or button measurements. |
| AT | Real servo | BLOCKED BY HARDWARE | GPIO unassigned, `ACTUATOR_OUTPUTS_ENABLED=0`, servo not connected/validated. |
| AU | Real water pump | BLOCKED BY HARDWARE | No pump connected/energized or electrical/flow measurements. |
| AV | Real integrated feeding | BLOCKED BY HARDWARE | No physical dispense/grams/final-success session; firmware always rejects FEED_REQUEST. |
| AW | Real integrated water | BLOCKED BY HARDWARE | No physical water-level feedback/pump control. |
| AX | Real cat dataset | BLOCKED BY DATASET | `ai/datasets/{raw,processed}` empty; no real labels/splits. |
| AY | Real identity model | BLOCKED BY DATASET | No weights or OWNER/OTHER false-acceptance study. |
| AZ | Real eating/drinking model | BLOCKED BY DATASET | No weights, real event labels or EATING↔DRINKING evaluation. |
| BA | End-to-end real prototype | BLOCKED BY HARDWARE | No Jetson+Logitech+ESP32+calibrated sensors+model+Web/App demonstration. |

## 3. What runs today on this Windows PC without Jetson, ESP32, Logitech or cat data

- **WORKING — local mock API:** From `jetson/`, launch `..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` and query `/api/v1/health`, `/status`, `/events`, `/daily-summary`. Camera/ESP32 label `MOCK`, sensors `NOT_CONNECTED`, empty history. POST `/feed/manual` uses a mock and returns PENDING after ACK, **not physical feeding or immediate SUCCESS**; tests can explicitly complete a mock result.
- **WORKING — software twin:** From `jetson/`, `..\.venv\Scripts\python.exe -m tools.run_simulator NORMAL` follows manually injected owner identity → mock REST request → simulated UART/feed policy → synthetic SUCCESS → synthetic event/typed history. `WATER_FILL_SUCCESS`, `OTHER_CAT`, `SERIAL_DISCONNECT` and the other defined scenarios likewise stay software-only. The tool does **not** identify an actual cat or control an ESP32.
- **WORKING — host safety/firmware checks:** From project root, `& .\scripts\run_checks.ps1` runs Python tests, dataset-empty validation, native C++ assertions/7 vectors, and both inert PlatformIO builds. No upload or GPIO operation.
- **WORKING — empty dataset tooling:** `python -m ai.scripts.dataset_report` and `python -m ai.scripts.prepare_training --task identity` return `DATASET_NOT_AVAILABLE`. Synthetic fixtures exercise import/labels/splits/evaluation; no real corpus is generated.
- **PREPARED, requires a supplied video file:** `VideoFileCameraProvider` / `python -m tools.replay_video --video PATH` can decode a compatible local file when OpenCV is installed, but repository tests use fake video frames; default mock models return UNKNOWN and generate no cat detections. `import_video` performs a dry-run until explicit `--apply`. No real file-to-classifier result is verified.
- **Historical PC-only camera evidence:** RC1 reports Windows camera index 0 read 83 frames at 640×480 and ~27.35 FPS, zero read failures, one temporary test frame. Windows PnP listed **HP Wide Vision HD Camera** (index-to-model association not independently proven). This is neither a Logitech nor Jetson result and is not repeated as hardware work in this audit.

## 4. Mock versus real: strict evidence matrix

YES/NO/PARTIAL/N/A apply **only to the named row**. “Real data” means validated cat/sensor observations, not synthetic fixtures or one PC inspection frame.

| Feature | Software implemented? | Simulation verified? | PC build verified? | Real hardware verified? | Real data verified? |
| --- | --- | --- | --- | --- | --- |
| REST health/status/events and mock feed | YES | YES | N/A | NO | NO |
| Typed SQLite and bounded event history | YES | YES | N/A | NO | NO |
| UART v1 CRC and seven golden vectors | YES | YES | YES | NO | N/A |
| Real pyserial transport / reconnect logic | YES | YES | N/A | NO | N/A |
| ESP32 inert parser/profile | YES | PARTIAL | YES | NO | N/A |
| Portable feed/water safety policies | YES | YES | YES | NO | NO |
| NVS safety counter adapter | PARTIAL | PARTIAL | YES | NO | NO |
| Actual HX711/ultrasonic/RTC sensing | PARTIAL | YES | YES | NO | NO |
| Actual servo/PWM and pump/MOSFET | NO | YES | YES | NO | NO |
| Windows camera index 0 (HP device listed by PnP; index mapping unconfirmed) | YES | N/A | N/A | YES | N/A |
| Logitech webcam → Jetson | YES | PARTIAL | N/A | NO | NO |
| Video replay / dataset utilities | YES | YES | N/A | NO | NO |
| Identity/behavior visual classifier | PARTIAL | NO | N/A | NO | NO |
| Temporal/fusion and eating/drinking records | YES | YES | N/A | NO | NO |
| Experimental food preference calculation | YES | YES | N/A | NO | NO |
| Existing Web/App integration | PARTIAL | NO | N/A | NO | NO |

## 5. Test/build verification and limits

This audit reran `scripts/run_checks.ps1` in the isolated Windows environment: **Python 99 total / 99 passed / 0 failed**; **one native C++ harness / 101 checks passed / 0 failed**; **7/7 common Python↔C++ UART vectors**; **21/21 defined simulator scenarios exercised across passing tests** (11 feed, 6 water, 4 identity/behavior-only; some are intentionally PENDING/rejected). Seeded serial tests include 1,000 random decode inputs, 500 noise/valid-stream cycles, CRC/length/resync cases; REST/metadata fuzz cases also pass. `ai/tests/test_dataset.py` tests empty state, synthetic images, labels, leaks and tool gates; real dataset report remains `DATASET_NOT_AVAILABLE`. Default SQLite inspection: schema 2, all three listed tables at 0 rows.

PlatformIO Core **6.2.0** with Arduino target `esp32dev`, pinned `espressif32@55.3.311`:

| Profile | PC build | RAM | Flash |
| --- | --- | --- | --- |
| `esp32dev_sim` | PASS | 22,692 / 327,680 B (6.9%) | 284,076 / 1,310,720 B (21.7%) |
| `esp32dev_hw_safe` | PASS | 22,692 / 327,680 B (6.9%) | 284,076 / 1,310,720 B (21.7%) |

**These results do not prove:** Jetson Python/JetPack/wheel compatibility or performance; Logitech detection, camera position/lighting; actual ESP32 board model/flash/NVS, physical CRC link or reconnect; sensor calibration; safe servo/pump electrical and mechanical behavior; AI performance on cats; food preference validity; or integration with the existing Web/App.

## 6. Weighted completion calculation

Checklist credits are **within each group**; 1 = code/design milestone evidenced, 0 = not implemented or no required real evidence. This conservative rubric gives no full real-system credit for mock-only outcomes and separately assigns zero to all real validation groups.

| Rubric group | Concrete checklist counted | Completed | Group completion | Weighted contribution |
| --- | --- | ---: | ---: | ---: |
| 1 Architecture & documentation (10%) | Current architecture; API/UART contracts; AI/data protocols; staged test/BOM/electrical plans; RC audit **done**. Exact as-built board/power/pin documentation **not possible yet**. | 5/6 | 83.33% | 8.33% |
| 2 Jetson backend/API/database (15%) | Host app/routes; generic events; typed SQLite/schema; durable feed lifecycle; typed queries/summary; configuration/local defensive limits **done**. Automatic vision→persistent observations and authenticated production access **not done**. | 6/8 | 75.00% | 11.25% |
| 3 ESP32 firmware/safety/control (20%) | Inert PC builds; UART parser; host feed policy; host water policy; NVS adapter/write-barrier code **done**. Real sensor implementations; RTC/display/button drivers; servo; pump; firmware dispatch of sensor/policy/final results **not done**. | 5/10 | 50.00% | 10.00% |
| 4 Communication/integration software (10%) | v1 codec/vectors; pyserial implementation; link manager; simulated API↔UART↔result **done**. MCU durable replay/operational FEED_STATUS and real water-status contract **not done**. | 4/6 | 66.67% | 6.67% |
| 5 Camera/video/data tooling (10%) | Abstraction/mock; PC USB probe/provider; replay interface; import/label; validation/report/session split **done**. Actual video decode/extract run on supplied footage and continuous camera→behavior pipeline **not evidenced**. | 5/7 | 71.43% | 7.14% |
| 6 AI/behavior software foundation (10%) | Model/data contracts; temporal smoothing; stable-weight fusion; experimental trend; daily/evaluation logic **done**. Real inference adapter; automated prediction→DB workflow; calibration with genuine events **not done**. | 5/8 | 62.50% | 6.25% |
| 7 Real dataset + trained AI (10%) | Real sessions, labels/split, trained identity, trained behavior: **none**. | 0/4 | 0% | 0% |
| 8 Real hardware validation (10%) | Jetson, Logitech on Jetson, flashed/linked ESP32, calibrated sensors/RTC, actuators: **none**. PC HP camera is not a substitute. | 0/5 | 0% | 0% |
| 9 Real-system integration/demo (5%) | Real feeding, real water, complete cat/Web/App demo: **none**. | 0/3 | 0% | 0% |

**OVERALL PROJECT COMPLETION = 8.33 + 11.25 + 10.00 + 6.67 + 7.14 + 6.25 + 0 + 0 + 0 = 49.64%.** **SOFTWARE/PRE-HARDWARE COMPLETION = 49.64 ÷ 75 available group-weight points = 66.19%.** Percentages are audit estimates tied to the above named checklist—not AI accuracy, project schedule or proof of future reliability. Groups overlap at boundaries (e.g. a host policy and its live firmware dispatch), but each row awards credit to a distinct deliverable.

## 7. Final user-facing goals: maturity stages

Stage meanings: DESIGNED = contract/plan, IMPLEMENTED = relevant host logic/API exists, SIMULATED = synthetic tests/scenario only. **No item below is REAL-DATA VERIFIED or REAL-HARDWARE VERIFIED** for the final Jetson/cat/ESP32 goal.

| Goal | Applicable stages now | Exact limitation |
| --- | --- | --- |
| 1 Recognize OWNER_CAT | DESIGNED | Enum/model interface only; mock returns UNKNOWN; simulator injects owner label, **not recognition**. |
| 2 Reject OTHER_CAT | DESIGNED, SIMULATED | OTHER_CAT scenario sends no automatic feed; no trained identity gate/real other-cat test. |
| 3 Recognize OTHER_OBJECT | DESIGNED | Label map/interface, no classifier. |
| 4 Detect EATING | DESIGNED, IMPLEMENTED, SIMULATED | Temporal logic consumes supplied synthetic EATING predictions; no visual detector. |
| 5 Detect DRINKING | DESIGNED, IMPLEMENTED, SIMULATED | Same, using water ROI/prediction input; no visual detector. |
| 6 Eating timestamps | DESIGNED, IMPLEMENTED, SIMULATED | UTC fields/session signal, no real cat event. |
| 7 Drinking timestamps | DESIGNED, IMPLEMENTED, SIMULATED | Typed drinking record, no real observation. |
| 8 Eating duration | DESIGNED, IMPLEMENTED, SIMULATED | Monotonic temporal test only. |
| 9 Drinking duration | DESIGNED, IMPLEMENTED, SIMULATED | Monotonic temporal test only. |
| 10 Estimate food consumed | DESIGNED, IMPLEMENTED, SIMULATED | Stable validated-sample guard; no calibrated load cell. |
| 11 Food preference | DESIGNED, IMPLEMENTED, SIMULATED | Experimental multi-session arithmetic with synthetic fixtures; zero valid food trials. |
| 12 Manual Feed | DESIGNED, IMPLEMENTED, SIMULATED | Mock POST lifecycle and host feed policy; physical SERIAL mode and firmware reject, button unconnected. |
| 13 Automatic feeding | DESIGNED | No owner-driven autonomous command or safe physical feeder. |
| 14 Daily feeding limits | DESIGNED, IMPLEMENTED, SIMULATED | Portable host C++/Python policy, not operational firmware control. |
| 15 Cooldown | DESIGNED, IMPLEMENTED, SIMULATED | Same, RTC/NVS untested on MCU. |
| 16 Automatic water maintenance | DESIGNED, IMPLEMENTED, SIMULATED | Local policy on host, firmware loop not controlling pump. |
| 17 Food-level monitoring | DESIGNED, SIMULATED | Synthetic available/empty flag and interface; no ultrasonic readings/driver. |
| 18 Water-level monitoring | DESIGNED, SIMULATED | Synthetic percentage; no physical water sensor. |
| 19 Local safety during Jetson failure | DESIGNED, IMPLEMENTED, SIMULATED | Policy independent of Jetson, link-loss scenarios; actual ESP32 local control not wired/tested. |
| 20 App/Web monitoring | DESIGNED, IMPLEMENTED, SIMULATED | Jetson API responds locally; existing frontend untested and private-LAN HTTPS/auth issues remain. |

## 8. Blockers in dependency order

1. **HARDWARE:** obtain/identify actual Jetson Nano/Logitech/ESP32; verify Jetson OS/Python/JetPack, webcam placement and ESP32 inert flash/USB communication (`PHASE2_MANUAL_STEPS.md`).
2. **ELECTRICAL:** confirm exact board pins, 3.3 V/ultrasonic ECHO level shifting, separate rated Jetson/actuator power, common ground, MOSFET/flyback and transient handling before wiring (`POWER_AND_ELECTRICAL_SAFETY.md`).
3. **HARDWARE + SOFTWARE:** bring up/calibrate HX711, DS3231/NVS, food/water sensors, then display/button/buzzer. Implement real drivers and connect validated inputs to the existing MCU policies; maintain disabled actuator guard during initial tests.
4. **MECHANICAL + SOFTWARE:** design/verify bowl, camera position, food gate, servo closure/jam detection, tubing/leak containment and physical pump/servo drivers. Define safe target amount and durable MCU replay/water telemetry before operational feeding; v1 feed request currently has no grams payload.
5. **DATASET:** supervised real cat video sessions across identities/behaviors/conditions, reliable food measurements, labels, quality checks and leakage-free splits (`DATA_COLLECTION_PROTOCOL.md`).
6. **AI:** compatible inference runtime/training and real held-out identity/behavior evaluation, especially OTHER_CAT→OWNER_CAT false acceptance and EATING↔DRINKING confusion; no current model weights.
7. **SOFTWARE + NETWORK:** join real predictions/sensors to persistent history, integrate frontend contract, authentication/TLS/private-network access and operating logs. This depends on validated APIs and recorded hardware behavior, not just host mocks.

## 9. Remaining worthwhile non-hardware work

**PRE-HARDWARE SOFTWARE IS SUFFICIENTLY COMPLETE for first Jetson/webcam/USB-serial bring-up**, not for a finished feeder. Optional narrow tasks, *not undertaken in this audit*:

| Candidate | Why useful / unlocks | Over-engineering risk |
| --- | --- | --- |
| Run existing `import_video` → `extract_frames` → `replay_video` on one explicitly supplied, non-cat local video | Tests actual OpenCV file/codec path; first real clip onboarding is less uncertain. No cat data/AI result required. | LOW; no new subsystem. |
| Small offline integration of **supplied** predictions → temporal engine → typed/generic history with idempotent sessions | Closes the currently separate replay/fusion/history path before real AI, useful for future reports. | MODERATE; data schema may change after first Jetson frames. Not required for initial hardware link. |
| Prepare an MCU wire-version/quantity/water-telemetry decision only after sensor/board facts | Avoids misusing v1 empty FEED_REQUEST and unreported water status before any physical action. | HIGH if implemented before hardware constraints; defer design commitment. |

## 10. Hardware arrival dependency order and next 10 **unfinished** tasks

No frontend change or cat training belongs ahead of proven camera/sensor inputs. Record evidence at each stage; see `HARDWARE_TEST_PLAN.md` for precautions.

| # | Task | Dependency | Hardware? | Cat data? | Completion evidence |
| ---: | --- | --- | --- | --- | --- |
| 1 | Inventory real Jetson OS/JetPack/Python; isolated runtime/tests | Jetson power/boot | YES | NO | `uname`/OS/model/Python output and full Jetson test counts |
| 2 | Detect Logitech on Jetson; measure frames/FPS/failures and fix intended bowl camera position | 1, webcam | YES | NO | device model/node, bounded `tools.test_webcam` log and inspected temp frame |
| 3 | Confirm ESP32 board and USB supply; build/flash inert HW_SAFE image | exact board, 1 | YES | NO | target revision, compile/upload log; no actuators attached |
| 4 | Jetson↔ESP32 USB PING/GET_STATUS, CRC/IDs, disconnect/reconnect and REST status | 1, 3 | YES | NO | physical serial traces and `/status` ONLINE/OFFLINE/recovery evidence |
| 5 | Verify exact pinout, level shifting, supplies, common ground and protection before sensor wiring | 3 | YES | NO | measured voltages, wiring/power plan, board-specific diagram |
| 6 | Calibrate HX711 with known masses, tare and disconnected/fault cases | 5 | YES | NO | repeated grams/error readings and fault logs |
| 7 | Test DS3231 valid/rollback time plus NVS reboot, same-day limits/inspection latch | 5, 6 | YES | NO | clock comparison, reboot/counter/fault logs |
| 8 | Validate food/water ultrasonic, then OLED/buzzer/button under output-disabled firmware | 5–7 | YES | NO | each sensor/indicator/button result and timeout/fault evidence |
| 9 | Implement/bench-test real drivers + policy dispatch and durable command outcomes **with actuator GPIO still disabled** | 4, 6–8 | YES | NO | firmware tests with measured inputs, reject/fault/final-result logs |
| 10 | After explicit electrical/mechanical review: servo with no food, **then** pump in isolated water rig, as separate supervised subtests | 5–9, gate mechanics | YES | NO | separately logged motion/stop/jam and pump/timeout/leak/power results |

Only **after** these: integrated feed/water rigs without an animal → passive supervised cat sessions/data → leak-safe labels and real model evaluation → real camera/sensor fusion → existing frontend/network integration → final demo. None is currently complete.

## 11. Data/AI and frontend readiness

**Identity OWNER_CAT/OTHER_CAT/OTHER_OBJECT:** enums, label map/schema, import/label/split/report tools, mock interface, evaluation including OTHER_CAT→OWNER_CAT false-acceptance arithmetic are ready (`app/ai/`, `ai/{dataset,training,evaluation}.py`); no cat data, trained model, runtime adapter or real false-acceptance rate. **Behavior EATING/DRINKING/OTHER:** behavior label schema, future model interface, temporal/session fusion and evaluation arithmetic are ready; no trained visual classifier, real event labels or event-level validation.

The repository **can accept a user-supplied video today** (not one already in the repo): from the project root, first run `python -m ai.scripts.import_video "PATH_TO_REAL_VIDEO.mp4" --session-id anonymous_session_001` (dry-run). Review the output, then explicitly add `--apply`. Decoding/extraction needs compatible OpenCV, the actual clip and separate quality review; no video was imported during this audit.

**Existing frontend readiness: PARTIAL.** Versioned routes, result polling/idempotency and documented responses exist (`API_V1_CONTRACT.md`). Actual old Flutter/Web request/response assumptions were **not inspected**, `/behavior` and `/drinking-history` are generic event lists not automatically populated by typed fusion records, physical manual feed intentionally rejects, sensors/water telemetry absent, local host binding defaults to `127.0.0.1`, and a hosted HTTPS browser cannot assume access to a private HTTP Jetson (mixed-content/local-network/CORS/auth/TLS; `OLD_FRONTEND_INTEGRATION.md`). Do not claim plug-and-play compatibility.

## 12. Technical debt, over-engineering and specific risks (no code changes)

**Debt / complexity:** legacy `esp32/include/hardware_interfaces.h::SafetyController::mayFeed` always returns false and overlaps newer `sensor_drivers.h`/`safety_logic.h`; C++ policies/NVS compile but `main.cpp` does not call feed/water `tick`; v1 FEED_REQUEST carries no target grams and SYSTEM_STATUS no water telemetry; ESP32 16-ID replay cache is volatile. Python has separate `MockEsp32Transport` and fuller `SimulatedEsp32Transport`, duplicate enum/data representations (`behavior/models.py:VisitRecord` vs `storage/records.py`, `FoodPreferenceEvidence` vs `PreferenceSummary`), and simulator detection by `type(...).__module__`. `main.py` constructs `TemporalEngine` but no live worker feeds it. `replay_video.py` defaults to UNKNOWN mocks; `video_file.py` assigns replay-relative timestamps, not original capture time. Dataset import is tested on a dummy file named `.mp4`, not codec decoding; near-duplicate comparison covers first 256, hash recheck first 1,000. Historical docs show earlier 38/88 tests, older footprints/Python support and must not replace RC1; `PRE_HARDWARE_RC1.md` is the current baseline. One PC camera test cannot imply Jetson readiness. These are observations, not requests to refactor now.

| Concrete risk | Current mitigation classification | Remaining evidence needed |
| --- | --- | --- |
| Jetson Python/JetPack/library compatibility | REQUIRES HARDWARE TEST | real version/import/full tests; host-only Python 3.14.3 |
| Jetson CPU/GPU inference/frame-rate capacity | REQUIRES HARDWARE TEST | measured pipeline latency on actual Jetson/model |
| Bowl/camera placement, occlusion | PARTIALLY MITIGATED; REQUIRES HARDWARE TEST | mounted camera observations across visits |
| Lighting, distance, view angle | PARTIALLY MITIGATED; REQUIRES DATASET TEST | labeled diversity/held-out sessions |
| OTHER_CAT falsely accepted as OWNER_CAT | PARTIALLY MITIGATED; REQUIRES DATASET TEST | real false-acceptance metric from held-out cats |
| EATING confused with DRINKING | PARTIALLY MITIGATED; REQUIRES DATASET TEST | real frame/event confusion and ROI checks |
| Load-cell drift/calibration/food-weight progress | PARTIALLY MITIGATED; REQUIRES HARDWARE TEST | known masses, tare, stability/fault trials |
| Ultrasonic echo/false levels | PARTIALLY MITIGATED; REQUIRES HARDWARE TEST | voltage/level-shift, wet/empty/timeouts |
| Servo jam/closing | PARTIALLY MITIGATED; REQUIRES HARDWARE TEST | independent electrical/mechanical stop tests |
| Pump dry run, electrical noise/leaks | PARTIALLY MITIGATED; REQUIRES HARDWARE TEST | isolated rig, current/flow/timeout tests |
| Jetson/actuator supply sag | PARTIALLY MITIGATED; REQUIRES HARDWARE TEST | actual PSU ratings/transient measurements |
| UART CRC, timeout, stale reply, disconnect | PARTIALLY MITIGATED; REQUIRES HARDWARE TEST | real USB disconnect/reconnect/CRC probes |
| Session leakage/near-duplicate frames | PARTIALLY MITIGATED; REQUIRES DATASET TEST | session-level split exists; real cross-session duplicates reviewed |
| Preference confounders | PARTIALLY MITIGATED; REQUIRES DATASET TEST | controlled multi-session food trials |
| MCU NVS interruption/idempotency and policy wiring | PARTIALLY MITIGATED; REQUIRES HARDWARE TEST | reset/power-loss/sensor and final-outcome tests |
| Public Web/App access/auth/TLS | PARTIALLY MITIGATED | real frontend contract/network/security design; no public deployment |

**Historical RC1 conclusion: milestone M2 only.** That checkpoint's99 Python tests, host assertions/builds and separate PC camera observation did not establish M3. Current maturity/verified counts are in `CURRENT_PROJECT_STATE.md` / `PRE_HARDWARE_FINAL_BASELINE.md`; the old checklist above is not an up-to-date feature inventory or milestone award.
