# M4 driver/component preparation — completed software scope, milestone M2

Historical snapshot navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL verification checkpoint:** this report's170 Python tests refer to the driver-preparation pass. Driver procedures remain useful; current overall counts/state are `PRE_HARDWARE_FINAL_BASELINE.md` / `CURRENT_PROJECT_STATE.md`. No M4 physical milestone is passed.

Date: 2026-10-03. **M3 pack not recreated. Milestone remains M2.** This pass implements missing real-I/O driver code and component-test firmware; it does not certify M3 communication or M4 physical sensing. No hardware was flashed, measured or calibrated. Candidate seller board remains unidentified; actual GPIO/memory/USB routing is unverified. No AI/data/physical completion credit is added. Prior conservative 49.64% overall / 66.19% software estimates are retained.

## Implementation matrix

| Component | Current implementation and host evidence | Physical boundary |
| --- | --- | --- |
| HX711 | Real ready/24-bit clock/signed decode/gain128 acquisition; timeout and rails; bounded raw average; tare/reference/grams; fake-pin pulse/data/timeout tests | No physical load cell, factor, measured grams or clock-timing validation |
| DS3231 | Real I²C presence/register read/write; strict BCD/calendar/12h/century/OSF; explicit UTC set and subsequent read; fake-bus tests | No RTC clock/retention/battery measurement |
| I²C scanner | 112 permissible addresses, one bounded probe per tick; explicit pins/timeout | ACK is not module identity; no real bus scan |
| Food ultrasonic | Trigger/echo state machine, bounded timeout/range, median5, separate full/empty calibration, optional percent | No actual voltage/range/geometry reading |
| Water ultrasonic | Separate instance/calibration, same real driver; shadow water-policy bridge with fresh sample counts and timers | No pump, actual level, flow or consumption measurement |
| SSD1306 | Minimal actual setup/128×32 or64 framebuffer/text/16-byte chunks; fake-bus complete-frame and fault tests | No panel identity/visual verification; no integrated all-sensor dashboard |
| Manual button | Actual configurable GPIO/polarity/pull plus debounce, short-release intent, boot-held/long-hold inhibition | No physical wiring/bounce result; intent rejected in safe firmware |
| Buzzer | Real GPIO on/off plus nonblocking confirm/warning/fault schedules; host tests | Active buzzer/driver assumption; passive tone generation not implemented |
| Servo | Typed disabled interface, request rejection, safeStop; no PWM/angles/pulse widths | Physical output remains prohibited |
| Pump | Typed disabled interface, OFF/ON/FAULT model, request rejection; no switching | Physical output remains prohibited |
| Health/snapshot | Seven health states, reasons, optional timestamped/fresh readings; validated/stale safety-input mapping | Not transported over frozen v1 or integrated as operational feeding |
| Sensor persistence | Separate 39-byte v1 CRC/flags/parameters codec; NVS load/save adapter | Codec host verified, adapter compiled; actual NVS retention/interruption unverified |

Headers are under `esp32/include/m4/`; actual GPIO/Wire/Preferences adapters are `arduino_io.h`. Components depend on injectable `PinIO`/`I2CBus`, allowing the actual acquisition classes to execute under fake I/O. `main.cpp` mode0 preserves normal firmware; `diagnostics.cpp` supplies explicitly selected component setup/loop. Initial findings are in `M4_DRIVER_AUDIT.md`.

## Verified tests and builds

Final full run of `scripts/run_checks.ps1`, after driver/diagnostic/fail-safe changes: **170 Python PASS**, imports PASS, dataset report `DATASET_NOT_AVAILABLE`/0 samples; old native safety harness **140 assertions PASS**, new driver harness **1188 assertions PASS**, unchanged UART **7/7 vectors**; compile guards **18/18 PASS**; all **11 firmware profiles PASS**. No code changed after this successful full regression.

Total native assertions: **1328 = 140 safety + 1188 driver**; these are assertions including repeated pulse checks, not 1328 independent test scenarios. All are host/fake evidence, not sensor samples. Host suite covers default/unreviewed/input-only pin rejection without I/O, signed HX711/pulse count/critical section/timeout/wrap/average fault separation, scale/level calibration, immediate invalidation of grams after tare/calibration load, record corruption, RTC/calendar/OSF/set failure, scanner bounds, ultrasonic edges/timeout/range/filter reset, both button polarities/pulls and bounce/long/boot holds, bounded buzzer/display, stale/nonfinite bridge input, shadow water hysteresis/freshness/timers and disabled actuator requests.

Compile guards retain all five original cases, reject servo/pump diagnostic enables, reject missing HW_SAFE/invalid mode/SIM mixing/invalid review/pull settings, and accept all six unassigned safe component modes. The firmware ASCII command handling is compiled/reviewed; an actual serial terminal/session, Arduino pin/bus timing and NVS operations require hardware. `run_checks.sh` is updated but not executed on Linux/Jetson in this Windows pass.

| Profile | Result | RAM B / 327680 | Flash B |
| --- | --- | ---: | ---: |
| `esp32dev_sim` | PASS | 24252 | 317672 / 1310720 |
| `esp32dev_hw_safe` | PASS | 24188 | 318464 / 1310720 |
| `esp32s3_n16r8_sim` | PASS | 24928 | 350328 / 6553600 |
| `esp32s3_n16r8_hw_safe` | PASS | 24864 | 351076 / 6553600 |
| `esp32s3_n16r8_hw_safe_uart` | PASS | 24164 | 330739 / 6553600 |
| `diag_hx711` | PASS | 26072 | 383752 / 6553600 |
| `diag_rtc` | PASS | 26064 | 382408 / 6553600 |
| `diag_i2c` | PASS | 26072 | 363200 / 6553600 |
| `diag_food_sensor` | PASS | 26064 | 382048 / 6553600 |
| `diag_water_sensor` | PASS | 26064 | 382444 / 6553600 |
| `diag_oled_button_buzzer` | PASS | 26064 | 364496 / 6553600 |

Toolchain: PlatformIO6.2.0, `espressif32@55.3.311`, Arduino3.3.11, Xtensa14.2.0+20260121; Python3.14.3; native Zig0.16.0 C++17. S3 uses official `esp32-s3-devkitc-1` compile surrogate with 16MB/QIO flash + OPI PSRAM configuration; compile success does not confirm those physical memories. Reported flash denominators are application partition limits, not a measured chip size.

## Safety and behavior boundaries

`ACTUATOR_OUTPUTS_ENABLED=0`, `SERVO_DIAGNOSTIC_ENABLED=0`, `PUMP_DIAGNOSTIC_ENABLED=0`; any enabled physical/diagnostic actuator configuration fails compilation. `pins.h` remains unassigned `-1`. All separate M4 GPIO defaults are `-1`, `M4_PINS_REVIEWED=0`; ultrasonic range/OLED address defaults force invalid configuration. No guessed seller pin map is committed.

HX711 readiness never busy-waits; only short critical-section conversion pulses use microsecond pauses. I²C uses explicit configuration, 100kHz and default25ms bounded per-transfer timeout. Ultrasonic edge state machines do not use `pulseIn`; pending acquisitions skip serial/report work and yield, with a 30ms default timeout. Button/buzzer/display use bounded ticks. Physical timing fidelity and the ultrasonic polling approach must be measured later.

Raw uncalibrated measurements may exist without grams/percent. No automatic healthy boot, compile-time RTC, scale factor, full reservoir, valid clock or physical actuator readiness is assumed. Invalid/missing measurements are null in reports. The safety bridge rejects invalid/nonfinite/out-of-range/stale evidence (2000ms software age limit). OLED failure does not grant or remove independent sensing authority. Safe component firmware never feeds; water request remains a hypothetical policy observation with physical pump false.

### Executed fail-safe integration tests

`esp32/test/native_drivers.cpp::failSafeIntegration` uses actual driver classes, snapshot mapping and the existing portable controllers. Hypothetical servo readiness and a fake counter store isolate policy prerequisites; they never enable a physical driver.

| Condition | Executed host outcome |
| --- | --- |
| HX711 ADC rail / readiness timeout / stale grams | FeedController REJECTED / HX711_FAULT, no open request or counter write |
| DS3231 oscillator-stop / absent valid time | FeedController REJECTED / RTC_INVALID, no open request or counter write |
| Food percent invalid | FeedController REJECTED / FOOD_EMPTY |
| HX711 fault during hypothetical dispensing | FeedController FAULT, desired-open cleared |
| Water below low / middle / above high | Stable low samples request hypothetical fill, middle retains it, high clears it |
| Actual portable ultrasonic timeout mapped to water inputs | WaterController SENSOR_FAULT, pump policy request false |
| SSD1306 packet failure | Feed safety ticks still execute and clear desired-open on a later weight fault; display does not manufacture validity |
| Button bounce / long hold / boot-held release | One short-release intent only; other sequences denied |
| Servo/pump disabled | Requests rejected, physical output false; enabled build flags rejected by compiler |

Diagnostic raw and filtered food/water distances are explicitly available in the local snapshot/ASCII report. Tare or calibration load immediately clears grams from a previous factor; a new factor waits for a new acquisition before reporting HEALTHY calibrated output.

## Commands, records and next physical step

Use `M4_DIAGNOSTIC_COMMANDS.md` for build/upload/monitor commands for every diagnostic (`COMx` / `ACTUAL_NODE` placeholders), reviewed local settings, commands, outputs and the **exact 12-step first HX711 workflow**: verified board → verified GPIO → voltage/power review → HX711-only connection → raw readings → stability → tare → known reference → factor → validation masses → repeatability → saved real evidence. Follow-ups cover explicit save/reboot/revalidate and readiness-loss faults. None of these physical steps was executed. RTC then food/water then UI component tests follow.

`SENSOR_CALIBRATION_RECORD.md` defines separate numerical sensor storage and a blank physical worksheet for reference/measured value, absolute/relative error, repeatability, environment, notes and PASS/FAIL (currently NOT_EVALUATED, no invented tolerance). `UART_SENSOR_STATUS_EXTENSION_PLAN.md` defines design work required before normal status gains sensor telemetry; frozen v1 remains unchanged. Normal HW_SAFE still rejects physical feeding; verified real sensing/policy integration and a negotiated telemetry contract remain future work.

## 27-point closeout

1. M3 pack: not recreated.
2. Driver audit: starting classifications and implemented end-state matrix in `M4_DRIVER_AUDIT.md`; sensor/UI paths IMPLEMENTED, actuators INTERFACE ONLY, physical results REQUIRES HARDWARE.
3. HX711: real bounded acquisition, raw average, tare/reference/grams/health; no fabricated default factor.
4. DS3231: real I²C presence/read/explicit set/strict validation; no compile-time fallback. Bounded scanner prepared separately.
5. Ultrasonic core: nonblocking trigger/echo/timeout/range/median filter, configured pins only.
6. Food level: independent calibrated geometry, valid distance-to-percent conversion/clamping; NOT_CALIBRATED before setup.
7. Water level: independent raw/filtered distance and percent, hysteresis/shadow state/request; physical pump always OFF.
8. OLED: minimal real SSD1306 transport/framebuffer/status; display faults independent of safety.
9. Button: polarity/pull/debounce/one short-release intent; no direct servo operation.
10. Buzzer: nonblocking active-buzzer confirmation/warning/fault patterns.
11. Servo interface: disabled requests/safe stop/health, no PWM/angles/pulse widths.
12. Pump interface: OFF/ON/FAULT abstraction, disabled requests, no physical switching.
13. Health/snapshot: all seven health states, optional raw/filtered/calibrated readings with timestamps/freshness; invalid/stale safety mapping.
14. Calibration persistence: separate 39-byte version/CRC record and explicit NVS load/save; no guessed factor/geometry, missing/invalid clears calibration.
15. Diagnostic firmware modes: HX711, RTC, I²C, food, water, OLED/button/buzzer; explicit mode selection, normal mode0 unchanged.
16. Diagnostic PlatformIO builds: all six S3 compile-surrogate profiles PASS with unassigned/review0 defaults.
17. New host tests: actual portable drivers with fake I/O, domain math/codec, and controller fail-safe integration; synthetic inputs are not hardware evidence.
18. Total Python tests: 170 PASS.
19. Total C++ assertions: 1328 PASS (140 existing safety + 1188 new driver), not independent scenario count.
20. UART vectors: frozen v1 7/7 PASS; one-byte GET_STATUS cannot carry the snapshot, so future versioned extension is documented only.
21. Compile guards: 18/18 PASS, preserving five original cases and enforcing new safe diagnostics/actuator restrictions.
22. All firmware builds: five existing safe + six diagnostic profiles = 11/11 PASS; footprints listed above.
23. Safety gates: three actuator flags0; production/component GPIOs unassigned; invalid configuration causes no pin access. Physical output is prohibited even if future permission booleans are true.
24. Immediately testable on arrival: identified board/reviewed settings + supplied HX711 → raw/tare/reference/error/fault/NVS workflow; subsequent RTC, separate levels and UI using prepared build/upload/monitor commands.
25. Impossible without hardware: actual identity/pins/voltages/timing/accuracy/calibration/RTC retention/NVS persistence and physical outputs; AI/data/final integration also remain unverified.
26. Exact first HX711 procedure: the 12 numbered steps in `M4_DIAGNOSTIC_COMMANDS.md`, followed by explicit NVS/reboot and readiness-loss tests; blank real-result worksheet prepared.
27. Freeze decision: **freeze this pre-hardware driver/component foundation for real bring-up**, milestone **M2**; hardware/AI/model/data/final integration remain incomplete, `AI_SHADOW_MODE=true`, dataset unavailable and AI untrained.
