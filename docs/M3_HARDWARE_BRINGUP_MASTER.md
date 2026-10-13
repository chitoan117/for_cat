# M3/M4 hardware bring-up master — preparation only, milestone M2

No stage is passed by this document, test suite or compile surrogate. Completion scores stay unchanged. M3 means **real Jetson + reviewed HW_SAFE ESP32 + physical USB PING/GET_STATUS/correlation/CRC + unplug/replug evidence**; sensors/actuators belong to M4. Recommended order is A–S below. D (webcam) is a separate recommended check, not an extra hidden M3 criterion.

Commands use the real project root (`$HOME/forr_cat` on Jetson) and actual observed node/COM, never an assumed port. On PC PowerShell from project root, `$Pio = Join-Path (Get-Location) '.tools-venv\Scripts\pio.exe'`. Initial ESP32-S3 target through the identified CH343G bridge is **`esp32s3_n16r8_hw_safe_uart`**, not native CDC and not SIM. The exact seller board is NOT VERIFIED.

**HISTORICAL pre-driver wording elsewhere in this pack is NOT CURRENT driver availability.** Sensor/UI diagnostic foundations are now implemented and compile-only verified; see `M4_DIAGNOSTIC_COMMANDS.md` for explicit modes/pin injection/commands. Normal PING/GET_STATUS firmware still does not provide real sensor telemetry. Physical pin/electrical/accuracy validation remains required, and no active servo/pump test driver or image exists. The original physical sequence below is retained, not rerun or awarded.

## A — Jetson board identification
- **PREREQUISITES:** physical board/carrier present, powered off; seller material available as reference.
- **CONNECTIONS:** none; ESP32/webcam/actuators disconnected.
- **COMMANDS:** manual read/photos only before boot; after safe power gate, `cat /proc/device-tree/model` if present.
- **EXPECTED RESULT:** actual Nano variant/carrier/revision/RAM markings recorded, not assumed from listing.
- **PASS CRITERIA:** photographs and matching board documentation identify the device.
- **FAIL CRITERIA:** uncertain/mismatching markings or unidentifiable carrier; defer power.
- **SAFETY WARNING:** don't attach a supply by connector shape alone.
- **EVIDENCE TO SAVE:** front/back photos, markings, source document links under `evidence/jetson/`.
- **NEXT GATE:** B only after identification.

## B — Jetson power verification
- **PREREQUISITES:** A and the exact board/revision supply requirements.
- **CONNECTIONS:** only reviewed Jetson supply; no actuator rail or ESP32.
- **COMMANDS:** manual supply/voltage/polarity check using appropriate instruments; no software substitutes for it.
- **EXPECTED RESULT:** safe correct input path/rating and stable standalone boot.
- **PASS CRITERIA:** supply identity/rating/wiring checked against actual board; no sag/reset/heating.
- **FAIL CRITERIA:** incorrect/unknown polarity, inadequate supply, resets or heat; power off.
- **SAFETY WARNING:** do not assume a weak shared 5 V source can power Jetson + MG996R + pump.
- **EVIDENCE TO SAVE:** supply label, wiring/input measurements, standalone boot notes.
- **NEXT GATE:** C.

## C — Jetson environment
- **PREREQUISITES:** A–B and source-only project copy; compatible interpreter plan.
- **CONNECTIONS:** Jetson only; no sensors/actuators.
- **COMMANDS:** from root `sh scripts/m3_check_jetson.sh` (optional explicit `--save`); if Python ≥3.10 and dependencies compatible, `sh scripts/setup_jetson.sh`, `. jetson/.venv/bin/activate`; from `jetson/`, core imports/readiness and applicable tests per `JETSON_FIRST_DAY.md`.
- **EXPECTED RESULT:** actual OS/kernel/L4T/JetPack/architecture/Python/pip/RAM/swap/disk/import state recorded.
- **PASS CRITERIA:** stable device plus successful core imports/tests or a clearly documented supported isolated environment; no PC results substituted.
- **FAIL CRITERIA:** unsupported Python/ABI/packages, failed imports/tests, resource problems; fix in isolation before service bring-up.
- **SAFETY WARNING:** diagnostic installs nothing; never replace JetPack/system Python blindly.
- **EVIDENCE TO SAVE:** timestamped diagnostic/test logs and versions in `evidence/jetson/`.
- **NEXT GATE:** D recommended, then E; unresolved environment blocks Jetson serial/API validation.

## D — USB webcam
- **PREREQUISITES:** C, compatible OpenCV, identified Logitech camera/data cable.
- **CONNECTIONS:** webcam → Jetson USB only.
- **COMMANDS:** from `jetson/`, `python -m tools.list_cameras`; explicitly select observed node, `python -m tools.benchmark_camera --device ACTUAL_VIDEO_NODE --seconds 5 --width 640 --height 480 --fps 10 --backend V4L2`.
- **EXPECTED RESULT:** actual frame dimensions/FPS/failures/backend; no automatic images/dataset saved.
- **PASS CRITERIA:** Logitech/device identity, readable frames and agreed measurement criteria logged on Jetson.
- **FAIL CRITERIA:** no node/permissions/frames or unstable capture; record failure, not a guessed FPS.
- **SAFETY WARNING:** no unattended private footage; PC HP camera result is not this result.
- **EVIDENCE TO SAVE:** node/model, benchmark command/output under `evidence/webcam/`.
- **NEXT GATE:** E; this check can be explicitly deferred for the narrower serial-only M3 minimum, not called passed.

## E — ESP32-S3 board identification
- **PREREQUISITES:** exact physical board and identity checklist; no peripherals attached.
- **CONNECTIONS:** none initially; reviewed USB development power only for detection.
- **COMMANDS:** manual photographs/markings; Windows `python -m serial.tools.list_ports -v` in prepared venv and Device Manager per `ESP32_S3_PC_DETECTION.md`.
- **EXPECTED RESULT:** WROOM variant/N16R8/antenna/revision/dual ports/CH343G and connector routing recorded.
- **PASS CRITERIA:** relevant `ESP32_S3_BOARD_IDENTITY_CHECKLIST.md` items checked with physical evidence/document cross-check.
- **FAIL CRITERIA:** listing differs, port/module/memory/power uncertain; stop before flash/pins.
- **SAFETY WARNING:** DevKitC-1 target is compile surrogate, not proof of seller pinout.
- **EVIDENCE TO SAVE:** photos, hardware IDs/seller/official references in `evidence/esp32/`.
- **NEXT GATE:** F.

## F — ESP32-S3 flash
- **PREREQUISITES:** E, inspected N16R8 compile settings/bridge routing; sensors/servo/pump disconnected.
- **CONNECTIONS:** identified CH343G port → development PC via data cable.
- **COMMANDS:** `& $Pio run -d esp32 -e esp32s3_n16r8_hw_safe_uart`; explicit upload `& $Pio run -d esp32 -e esp32s3_n16r8_hw_safe_uart -t upload --upload-port ACTUAL_COM`; hash/monitor/probe per `ESP32_S3_FIRST_FLASH.md`.
- **EXPECTED RESULT:** successful upload/boot with safe banner/profile and valid PC PING/GET_STATUS; no Wi-Fi required.
- **PASS CRITERIA:** actual target/module reviewed, upload/hash and boot `actuator_enabled=0 simulation=0 SAFE_BUILD_ACTUATORS_DISABLED` evidence, valid PC replies.
- **FAIL CRITERIA:** wrong image/port, SIM banner, unverified memory/routing, upload/reset/CRC errors; do not proceed.
- **SAFETY WARNING:** monitor must close before probing; GET_STATUS byte 01 proves responsiveness, not firmware identity or safety.
- **EVIDENCE TO SAVE:** image SHA256/build/upload/boot/PC probe logs and port photos in `evidence/esp32/`.
- **NEXT GATE:** G; PC-only success is not M3.

## G — Jetson ↔ ESP32 serial (M3 minimum link gate)
- **PREREQUISITES:** C/E/F and safe board USB power; one host/monitor at a time.
- **CONNECTIONS:** identified CH343G port → real Jetson USB; all peripherals/actuators disconnected.
- **COMMANDS:** discover `ls -l /dev/ttyUSB* /dev/ttyACM*`; from `jetson/`, `python -m tools.test_serial --device ACTUAL_SERIAL_NODE --m3 --count 3 --interval 1 --json`. Manually unplug, repeat one probe against old node; reconnect/rediscover and repeat. Optional deliberately configured API `/status` may record OFFLINE/recovery; `/health` alone does not test serial.
- **EXPECTED RESULT:** PING ACK 01 / SYSTEM_STATUS 01, matching IDs and valid CRC; RTT/timeouts logged; disappearance then recovery.
- **PASS CRITERIA:** all exact `M3_M4_GATE_DEFINITION.md` minimum items have real dated Jetson+ESP32 evidence, including disconnect/reconnect timing and final PING/GET_STATUS.
- **FAIL CRITERIA:** mismatch/CRC failure/timeout while connected, no disconnect detection or no recovery; no M3 declaration.
- **SAFETY WARNING:** only PING/GET_STATUS, no FEED_REQUEST; close other serial users. First RTT can include USB-open/reset wait; do not label it pure steady-state latency.
- **EVIDENCE TO SAVE:** connected/unplugged/reconnected node listings, JSON/RTT/CRC/request logs, UTC action times, API states if tested under `evidence/serial/`.
- **NEXT GATE:** manually reviewed M3 eligibility, then H for M4 preparation; this pack itself remains M2.

## H — GPIO/electrical review
- **PREREQUISITES:** identified board/M3, datasheets/schematic, instruments and power-tree review.
- **CONNECTIONS:** no sensors/actuators driven; power off for wiring review.
- **COMMANDS:** manual `GPIO_FINALIZATION_WORKSHEET.md`, `GPIO_VOLTAGE_PLAN.md`, power-tree measurements; no GPIO-write script.
- **EXPECTED RESULT:** documented candidate/capability/routing/3.3 V protection decisions.
- **PASS CRITERIA:** each proposed pin checked for input/output/PWM/I2C, straps, USB/JTAG and flash/PSRAM; voltage/power protection verified.
- **FAIL CRITERIA:** assumed seller pinout, direct 5 V ECHO, conflicts or unknown power paths; leave pins unassigned.
- **SAFETY WARNING:** current source hard-disables outputs; completed worksheet does not remove that guard.
- **EVIDENCE TO SAVE:** approved diagrams/measurements/pin-source references in component folders.
- **NEXT GATE:** approved sensor-only test firmware prerequisite, then I.

## I — HX711 + load cell
- **PREREQUISITES:** H, reviewed real bounded driver/test image and mounted cell; see `HX711_LOADCELL_BRINGUP.md`.
- **CONNECTIONS:** reviewed excitation/differential/DOUT/SCK/logic supply, no servo/pump.
- **COMMANDS:** no current raw-weight tool; after approved sensor-only image, its reviewed test interface plus `pio device monitor --port ACTUAL_COM --baud 115200`.
- **EXPECTED RESULT:** raw/stability/tare/known masses/calibration/error/fault measurements.
- **PASS CRITERIA:** agreed calibration/repeatability accuracy and explicit sensor timeout/fault behavior recorded.
- **FAIL CRITERIA:** guessed factor, drift/rail values/overload, invalid data shown healthy.
- **SAFETY WARNING:** no guessed wire colors or logic voltage; no actuator/animal.
- **EVIDENCE TO SAVE:** raw/calibrated traces, mass standards/mount/tolerance/factor in `evidence/hx711/`.
- **NEXT GATE:** J; weight consumption/feeding still unvalidated.

## J — DS3231
- **PREREQUISITES:** H and approved bounded RTC/I2C test image; battery/module identified.
- **CONNECTIONS:** reviewed I2C/pull-ups/backup-cell arrangement, actuators disconnected.
- **COMMANDS:** future image scan/read/set commands only (not supplied now), serial monitor; no Jetson i2cdetect proof for an ESP32-wired RTC.
- **EXPECTED RESULT:** clock read/set/restart/backup/date-rollover and invalid-time behavior.
- **PASS CRITERIA:** declared clock tolerance and safe invalid/rollback detection; NVS interaction tested later.
- **FAIL CRITERIA:** wrong bus voltage/address, invalid/lost time accepted or unsafe battery charging.
- **SAFETY WARNING:** match cell chemistry/module charging circuit; no feeding on invalid RTC.
- **EVIDENCE TO SAVE:** reference/set/read/retention/rollover traces in `evidence/rtc/`.
- **NEXT GATE:** K.

## K — Food-level sensor
- **PREREQUISITES:** H, module identity/ECHO protection and approved sensor-only test image.
- **CONNECTIONS:** reviewed TRIG/ECHO/supply with safe level shift; water sensor/pump not operating.
- **COMMANDS:** future bounded driver/test output and serial monitor; current HW_SAFE reads no distance.
- **EXPECTED RESULT:** raw/filtered distance, invalid echoes, usable range and hopper conversion/hysteresis.
- **PASS CRITERIA:** declared tolerance and stable actual geometry transitions/fault indication.
- **FAIL CRITERIA:** direct 5 V, wall/blind-zone errors/chatter or fake full/empty on invalid echo.
- **SAFETY WARNING:** no dispense based on this independent range test.
- **EVIDENCE TO SAVE:** targets/geometry/range/fault readings in `evidence/food_sensor/`.
- **NEXT GATE:** L.

## L — Water-level sensor
- **PREREQUISITES:** H, JSN revision/blind-zone/level shift reviewed, approved driver/test image.
- **CONNECTIONS:** protected electronics/echo, real container/transducer; pump disconnected.
- **COMMANDS:** future reviewed raw/filtered/validity output and serial monitor; see `WATER_LEVEL_SENSOR_BRINGUP.md`.
- **EXPECTED RESULT:** measured water reflections/range/mounting/condensation and invalid-echo behavior.
- **PASS CRITERIA:** repeatable real-container levels and fault/hysteresis evidence within agreed tolerance.
- **FAIL CRITERIA:** blind-zone/condensation/wall echo mistaken for healthy full/empty.
- **SAFETY WARNING:** waterproof transducer does not waterproof the PCB; keep water away from electronics.
- **EVIDENCE TO SAVE:** distances/conditions/level mapping/fault logs in `evidence/water_sensor/`.
- **NEXT GATE:** M.

## M — OLED
- **PREREQUISITES:** H/J, reviewed accessory-only I2C/display driver/test image.
- **CONNECTIONS:** verified display/pull-ups/address only, no actuators.
- **COMMANDS:** future display status test and monitor; current source only has interface/simulation.
- **EXPECTED RESULT:** actual status shown, display/bus failures bounded.
- **PASS CRITERIA:** readable status and display fault cannot block safety/control.
- **FAIL CRITERIA:** wrong voltage, stuck I2C/display path or unconnected sensor displayed healthy.
- **SAFETY WARNING:** OLED is an indicator, not feeding safety authority.
- **EVIDENCE TO SAVE:** photos/fault/control-response logs in `evidence/esp32/`.
- **NEXT GATE:** N.

## N — Buzzer
- **PREREQUISITES:** H, buzzer/driver type and approved non-blocking test image.
- **CONNECTIONS:** reviewed current-limited/driver circuit; actuators disconnected.
- **COMMANDS:** future short scheduled-alert test and monitor, no present activate command.
- **EXPECTED RESULT:** bounded alert while control/protocol remains responsive.
- **PASS CRITERIA:** duration/responsiveness/current acceptable and reset safe.
- **FAIL CRITERIA:** blocking control, stuck alarm, excess current or heat.
- **SAFETY WARNING:** do not source unsuitable buzzer current from GPIO; use safe sound exposure.
- **EVIDENCE TO SAVE:** duration/control/current observations in `evidence/esp32/`.
- **NEXT GATE:** O.

## O — Manual Feed button
- **PREREQUISITES:** H, input polarity/pull defined, approved debounced button test image.
- **CONNECTIONS:** reviewed input/ground/pull-up/down only; no servo/pump power.
- **COMMANDS:** future button intent log; press/hold/release/bounce independently, monitor output.
- **EXPECTED RESULT:** stable released boot, one intent per valid press, disabled-build rejection.
- **PASS CRITERIA:** measured debounce/no duplicate/boot intent and safety precheck remains authoritative.
- **FAIL CRITERIA:** floating/strap input, held button reissues unintended feeds, or unsafe actuation.
- **SAFETY WARNING:** do not confuse BOOT with a safe Manual Feed input without exact pin review.
- **EVIDENCE TO SAVE:** wiring/polarity/debounce/event traces in `evidence/esp32/`.
- **NEXT GATE:** separate approval for P, not automatic output enablement.

## P — Servo unloaded test (later gate)
- **PREREQUISITES:** H–O, power/mechanical review and separately approved bounded actuator-test image; current hard-disabled firmware cannot move it.
- **CONNECTIONS:** external adequate servo rail + reviewed signal/reference ground, no food/load/animal.
- **COMMANDS:** no current actuator command; only a future reviewed unloaded bounded-motion interface, not REST GPIO.
- **EXPECTED RESULT:** small controlled movement/closure/endpoints with current/reset/jam-timeout observations.
- **PASS CRITERIA:** `SERVO_BRINGUP.md` motion/current/safe-stop criteria actually measured.
- **FAIL CRITERIA:** runaway/jam/heat/current issue, reset or unconfirmed closure.
- **SAFETY WARNING:** never power MG996R from Jetson/ESP32 logic rail or GPIO; no guard-removal shortcut.
- **EVIDENCE TO SAVE:** image hash, motion/current/logs/endpoints in `evidence/servo/`.
- **NEXT GATE:** Q.

## Q — Pump isolated test (later gate)
- **PREREQUISITES:** H–O, MOSFET/flyback/power/contained-rig review and approved bounded pump-test image.
- **CONNECTIONS:** separate pump rail, correct 3.3 V gate/return/protection, no Jetson supply path/animal.
- **COMMANDS:** no current pump command; future explicitly reviewed short pulse/timeout test only.
- **EXPECTED RESULT:** controlled flow/off, no leaks/resets, timeout/progress/fault stop.
- **PASS CRITERIA:** `PUMP_BRINGUP.md` measured current/noise/runtime/leak/off evidence.
- **FAIL CRITERIA:** stuck output, dry run/overflow/heating, reset/noise or missing stop.
- **SAFETY WARNING:** water/electronics separated; ESP32, not Jetson, must stop the pump locally.
- **EVIDENCE TO SAVE:** current/voltage/flow/timeout/leak logs/photos in `evidence/pump/`.
- **NEXT GATE:** R and S only after both actuator subtests and mechanism approval.

## R — Integrated feeding mechanism
- **PREREQUISITES:** calibrated sensor/RTC/local limits/servo evidence, reviewed mechanics and operational safety firmware; no animal.
- **CONNECTIONS:** reviewed complete food rig and supply paths, supervised stop/disconnect available.
- **COMMANDS:** no current integrated physical test exists; later approved intent/policy test interface only (no raw GPIO API).
- **EXPECTED RESULT:** weighed dispense, close, correct counters/cooldown/limits, faults/off/reset/link-loss handling and final result separate from ACK.
- **PASS CRITERIA:** declared target/error/runtime limits and real fault/recovery evidence; no duplicate physical portion for a retried key.
- **FAIL CRITERIA:** overfeed/jam/no progress, counter loss/duplicate dispense, unsafe boot or ACK called success.
- **SAFETY WARNING:** inert HW_SAFE cannot perform this; explicit later firmware/output review required before power.
- **EVIDENCE TO SAVE:** mechanism photos, mass/timing/result/counter/fault traces in `evidence/servo/` and `hx711/`.
- **NEXT GATE:** S; M4 is not complete until both integrated basic operations and component evidence pass.

## S — Integrated water system
- **PREREQUISITES:** validated level/RTC/pump/power/contained-rig evidence and reviewed local safety firmware.
- **CONNECTIONS:** supervised water rig, no animal, safe electronics/power isolation.
- **COMMANDS:** no current integrated physical test exists; later approved local water-policy interface/monitor only.
- **EXPECTED RESULT:** low→fill→recovered OFF, hysteresis/no chatter, faults/no progress/max runtime/local stop under Jetson loss.
- **PASS CRITERIA:** real level/flow/off/reset/fault traces show bounded safe operation plus all M4 components separately verified.
- **FAIL CRITERIA:** overflow/leak, noise/reset, unhealthy sensor accepted or pump depends on Jetson to stop.
- **SAFETY WARNING:** never substitute simulated pump state for measured output; supervise isolation/leaks.
- **EVIDENCE TO SAVE:** container/mount/level/flow/current/fault/result logs in `evidence/water_sensor/` and `pump/`.
- **NEXT GATE:** manual M4 review only; dataset, AI training and animal observation require separate later approval.
