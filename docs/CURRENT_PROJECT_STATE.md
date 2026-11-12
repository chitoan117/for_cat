# CURRENT project state — forr_cat

> **Chỉ dẫn cập nhật 26/10/2026:** nội dung bên dưới là checkpoint lịch sử của checkout Windows cũ, có trạng thái/pin RTC đã lỗi thời so với các phiên sau.
> Dùng [PROJECT_STATUS_20261026.md](PROJECT_STATUS_20261026.md) và [OFFLINE_RELEASE_20261026.md](../OFFLINE_RELEASE_20261026.md) để bàn giao hiện tại.
> Không dùng bảng legacy bên dưới làm quyền flash/đấu lại GPIO16/17/18 hoặc tuyên bố runtime/physical mới. Phiên RC không truy xuất Jetson.

**Primary human-readable source of truth. Current stage: REAL M3 evidence closeout / M4 SENSOR-ONLY PREPARATION.** Normal USB webcam → Jetson Nano → USB serial → ESP32-S3 chip with measured16MB flash, **PSRAM NOT DETECTED** → sensors/UI/future servo/pump; Web/App↔REST↔Jetson. ESP32-S3 is final actuator authority. Seller N16R8/8MB claim is not current software truth; pins/voltage/sensors/actuators remain unverified. Canonical architecture unchanged.

**RTC hardware changed from planned DS3231 to available DS1302 during M4 physical bring-up.** Canonical `diag_rtc`/snapshot RTC is DS1302,CLKGPIO16,DAT/IOGPIO17bidirectional,CE/RSTGPIO18;OLEDI2ConlySDA8/SCL9. No0x68RTCexpectation. RTC2000–2099/CH/WP/readbacksoftware semantics tested, noautobootset. See `DS1302_BRINGUP.md` / `DS1302_MIGRATION_RESULT.md`; physicalRTC/sensorvalidation stillNOT PERFORMED, gates/output0/shadowtrue/v1unchanged.

User-supplied physical facts: Nano2GB/Ubuntu18.04.6/L4T32.7.6/Python3.6.9/working reported GPU/OpenCV stack; Generic Web Camera4a54:5233,/dev/video0,720pMJPG300frames/0fail/10.008s/29.97FPS; S3revv0.2/40MHz/flash16MB;1a86:55d3 bridge/cdc_acm,/dev/ttyACM0,pyserial3.5; no-stub factory flash/hash/reset; initial PING100/GET_STATUS101 IDs/CRC PASS,unplug/re-enumeration PASS. Post-reconnect protocol **USER-REPORTED PASS**, no raw transcript supplied. Record `M3_PHYSICAL_VALIDATION_RECORD.md` / `evidence/M3_REAL_HARDWARE_FACTS.json` preserves null dates/rawCRC/rawhex/imagehash, not fabricated logs. Formal milestone closeout remains M2→M3 pending dated reconnect proof; no M4 PASS.

| Newly observed subsystem | Actual supplied evidence | Remaining limitation |
| --- | --- | --- |
| Jetson runtime environment | Physical boot/versions reported | Full modern API not run: system3.6 cannot import modern backend |
| Webcam | Physical1280×720MJPG29.97FPS test reported |1080p only advertised; new provider/utility not physically rerun here |
| S3 chip/flash | ROM reportedS3v0.2/16MB/40MHz |PSRAM NOT DETECTED; no N16R8 inference |
| Serial link | Initial actual PING/GET_STATUS/IDs/CRC and node loss/recovery reported |Post-reconnect exact frames/date/hash not stored |
| M4 sensor/UI/actuator hardware |No physical test supplied |Only candidate pin/profile/host builds;servo/pump remain-1/output0 |

The detailed table below retains the **pre-hardware checkpoint** layers for chronology, not today's blanket hardware status. New physical facts above supersede its NO entries only within their named user-reported scope. Latest adaptation test/build totals are recorded in `REAL_HARDWARE_ADAPTATION_RESULT.md` after execution.

Current DS1302migration host check: **309 Python PASS,3451 native assertions PASS (140+3311),UART7/7,guards46/46,builds18/18**, actuallyexecuted2026-10-09T02:32:53.153670+00:00. Nativeadds180DS1302riskassertions;7additionalRTCguardcases,existingtestsvectorspreserved. `DS1302_MIGRATION_RESULT.md` / `.checks/summary.json` are currenthostscope,notphysicalRTCresults. Previousno-PSRAMadaptation309/3271/39/18at2026-10-08remainschronologyin `REAL_HARDWARE_ADAPTATION_RESULT.md`; pre-hardwarecutoff301/3271/18/11ishistorical. N/A/PASSbelowarelayer-specific,notphysicalRTC/actuatorPASS.

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
| RTC/DS1302 (current selection) |Yes, three-wire/read/explicitset/BCD/CH/WP/readback |NativefakeGPIOtested |Syntheticclockprotocol/faults |diag_rtctested |NO |NOreference/retention |GenericRTC_INVALID/day/cooldownpreserved; legacyDS3231tableclaimsarehistorical |
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
