# M4 component diagnostics

Implemented in `esp32/src/diagnostics.cpp` and `esp32/include/m4/`. PC compilation and fake-I/O tests are complete; **NOT HARDWARE VERIFIED**. Milestone remains M2. These images use human **ASCII at 115200 baud**, not binary UART v1; use a serial terminal, not the Jetson v1 transport/test tool.

## Select a component explicitly

From `esp32/`, compile only:

```powershell
..\.tools-venv\Scripts\pio.exe run -e diag_hx711
..\.tools-venv\Scripts\pio.exe run -e diag_rtc
..\.tools-venv\Scripts\pio.exe run -e diag_i2c
..\.tools-venv\Scripts\pio.exe run -e diag_food_sensor
..\.tools-venv\Scripts\pio.exe run -e diag_water_sensor
..\.tools-venv\Scripts\pio.exe run -e diag_oled_button_buzzer
```

Normal SIM/HW_SAFE images have `M4_DIAGNOSTIC_MODE=0` and retain binary v1. Modes 1–6 require HW_SAFE and reject SIM. All actuator flags remain 0; enabling servo/pump diagnostic flags fails compilation. S3 environments are **compile surrogates**, not proof of the seller board's pin routing, CH343G port, 16 MB flash or 8 MB PSRAM.

## Configuration before future physical use

Default pins are `-1`, review flag is 0, ultrasonic limits and OLED address are 0. Drivers reject these configurations before pin mode/read/write or I²C transfers. Missing measurement is `null`, never assumed zero/full/healthy.

After identifying the actual board/module and reviewing its wiring, create a local environment inheriting the appropriate diagnostic environment. Preserve all inherited flags using `${env:diag_hx711.build_flags}` (or the corresponding environment). Add only measured/reviewed values for the selected component. No final GPIO assignment is supplied here.

| Component | Local compile settings |
| --- | --- |
| All configured pins | `M4_PINS_REVIEWED=1` only after physical review |
| HX711 | `M4_HX711_DOUT`, `M4_HX711_SCK` |
| RTC/scanner/OLED | `M4_I2C_SDA`, `M4_I2C_SCL` |
| Food ultrasonic | `M4_FOOD_TRIG`, `M4_FOOD_ECHO`, `M4_ULTRASONIC_MIN_CM`, `M4_ULTRASONIC_MAX_CM` |
| Water ultrasonic | `M4_WATER_TRIG`, `M4_WATER_ECHO`, same explicit module limits |
| OLED | `M4_OLED_ADDRESS` (identified 0x3c/0x3d), `M4_OLED_HEIGHT` (32/64) |
| Button | `M4_BUTTON_PIN`, `M4_BUTTON_ACTIVE_LOW` (default 1), `M4_BUTTON_PULL` (0 none, 1 up, 2 down) |
| Buzzer | `M4_BUZZER_PIN`; current adapter is active-high on/off, for an active buzzer/driver |

The Arduino adapter conservatively excludes MCU memory/strap/USB/JTAG/UART pins and checks input/output capability. Review is still essential: exclusions do not describe the unidentified board's headers or external circuitry. Check I²C pull-up voltage and HX711 logic supply; condition a 5 V ultrasonic ECHO before any ESP32 connection. Servo/pump remain disconnected for these component tests.

## Future build, upload and monitor commands

**Prepared commands only: no upload or monitor has been executed.** Run from `esp32/`. `COMx` and `ACTUAL_NODE` are placeholders, not detected devices. Replace them with the identified board's port. Before measuring, inject the reviewed settings above into the selected environment or its local inherited variant, retaining all original safety/memory flags. Substitute the variant's environment name in every command if used. The unassigned base images only exercise CONFIGURATION_INVALID behavior.

Windows executable variable:

```powershell
$Pio = '..\.tools-venv\Scripts\pio.exe'
```

| Diagnostic | Build | Future upload | Future monitor |
| --- | --- | --- | --- |
| HX711 | `& $Pio run -e diag_hx711` | `& $Pio run -e diag_hx711 -t upload --upload-port COMx` | `& $Pio device monitor --port COMx --baud 115200` |
| RTC | `& $Pio run -e diag_rtc` | `& $Pio run -e diag_rtc -t upload --upload-port COMx` | `& $Pio device monitor --port COMx --baud 115200` |
| I²C | `& $Pio run -e diag_i2c` | `& $Pio run -e diag_i2c -t upload --upload-port COMx` | `& $Pio device monitor --port COMx --baud 115200` |
| Food | `& $Pio run -e diag_food_sensor` | `& $Pio run -e diag_food_sensor -t upload --upload-port COMx` | `& $Pio device monitor --port COMx --baud 115200` |
| Water | `& $Pio run -e diag_water_sensor` | `& $Pio run -e diag_water_sensor -t upload --upload-port COMx` | `& $Pio device monitor --port COMx --baud 115200` |
| OLED/button/buzzer | `& $Pio run -e diag_oled_button_buzzer` | `& $Pio run -e diag_oled_button_buzzer -t upload --upload-port COMx` | `& $Pio device monitor --port COMx --baud 115200` |

Linux/Jetson, with an installed PlatformIO CLI (not executed here):

| Diagnostic | Build | Future upload | Future monitor |
| --- | --- | --- | --- |
| HX711 | `pio run -e diag_hx711` | `pio run -e diag_hx711 -t upload --upload-port ACTUAL_NODE` | `pio device monitor --port ACTUAL_NODE --baud 115200` |
| RTC | `pio run -e diag_rtc` | `pio run -e diag_rtc -t upload --upload-port ACTUAL_NODE` | `pio device monitor --port ACTUAL_NODE --baud 115200` |
| I²C | `pio run -e diag_i2c` | `pio run -e diag_i2c -t upload --upload-port ACTUAL_NODE` | `pio device monitor --port ACTUAL_NODE --baud 115200` |
| Food | `pio run -e diag_food_sensor` | `pio run -e diag_food_sensor -t upload --upload-port ACTUAL_NODE` | `pio device monitor --port ACTUAL_NODE --baud 115200` |
| Water | `pio run -e diag_water_sensor` | `pio run -e diag_water_sensor -t upload --upload-port ACTUAL_NODE` | `pio device monitor --port ACTUAL_NODE --baud 115200` |
| OLED/button/buzzer | `pio run -e diag_oled_button_buzzer` | `pio run -e diag_oled_button_buzzer -t upload --upload-port ACTUAL_NODE` | `pio device monitor --port ACTUAL_NODE --baud 115200` |

Close other serial clients before upload/monitor; diagnostics use human ASCII. Capture the terminal transcript with its actual board/port/settings into real evidence. No device discovery, upload, monitoring or measurements run automatically.

## Commands

One printable ASCII line, CR/LF terminated; maximum 95 characters, 32 bytes consumed per loop. Overflow/control-character lines are discarded. Trailing extra arguments are rejected. `N` is 1–64 (one/two decimal digits). Unknown commands are rejected. No command actuates a servo or pump.

| Command | Mode | Effect |
| --- | --- | --- |
| `help`, `status` | All | Help / current diagnostic snapshot |
| `avg N` | HX711 | Average the next N valid raw conversions |
| `tare N` | HX711 | Capture empty-platform average; invalidates previous scale factor |
| `cal GRAMS N` | HX711 | Known positive measured reference mass, next N conversions; requires tare |
| `validate GRAMS N` | HX711 | Measured grams plus absolute/relative error; does not assign PASS tolerance |
| `food-geometry FULL_CM EMPTY_CM` | Food | Set measured sensor-to-surface distances; requires `0 < full < empty` |
| `water-geometry FULL_CM EMPTY_CM` | Water | Separate measured geometry; never reuses food geometry |
| `load` | All | Load sensor record; missing/invalid record clears calibration |
| `save YES` | All | Explicitly persist valid calibration; does not modify safety counters |
| `scan` | I²C scanner | Probe 0x08–0x77, one bounded transfer per loop |
| `set-utc YYYY-MM-DDTHH:MM:SSZ CONFIRM` | RTC | Explicit valid UTC date/time; subsequent read is required |
| `buzz confirm`, `buzz warning`, `buzz fault` | OLED/button/buzzer | Nonblocking on/off pattern |

Do not calibrate while the platform is moving. A new averaging command replaces an earlier pending one. Sensor timeout/ADC fault aborts a pending average, clears its validity, and prevents mixing samples across the fault. Starting another average is explicit.

Tare/loading calibration clears any grams computed with the previous factor immediately. A newly calculated factor waits for a new raw sample before reporting grams/HEALTHY. `load` also cancels a pending average; recalculating level geometry does not count as a new echo sample for water stability.

RTC never adopts compile time, PC time or a guessed time automatically. Oscillator-stop status or invalid BCD/date prevents valid RTC output. Scanner ACK identifies only a responding address, not a verified module.

## Output meaning

Startup banner labels HW_SAFE, selected mode and all disabled actuator flags. Periodic JSON includes monotonic time, component health/reason, raw counts, grams, optional RTC UTC epoch, food/water distance and percentage, water policy state/reason, OLED/button/buzzer health, `hardware_verified:false`, and `physical_pump_on:false`.

- Health: `NOT_CONFIGURED`, `NOT_CONNECTED`, `NOT_CALIBRATED`, `INITIALIZING`, `HEALTHY`, `DEGRADED`, `FAULT`. These are runtime software classifications; `HEALTHY` does not certify hardware validation.
- Water states: 0 SAFE_BOOT, 1 NORMAL, 2 FILLING, 3 FAULT. Reasons: 0 NONE, 1 SENSOR_FAULT, 2 PUMP_FAULT, 3 NO_PROGRESS, 4 TIMEOUT.
- Water `would_request_pump` uses the existing policy with an explicitly **hypothetical ready pump**. It is not a physical output or pump health result. New samples drive stability counts; filling timers and invalid/stale inputs are checked between samples.
- Button short release emits `FEED_INTENT REJECTED SAFE_BUILD_ACTUATORS_DISABLED`; held-at-boot release, long holds and bounce produce no feeding operation.
- SSD1306 displays status text. Its failure never bypasses sensor prerequisites. This component mode does not collect other modes' sensors concurrently; their unconfigured status is expected.
- Ultrasonic reports include `food_raw_distance_cm`/`water_raw_distance_cm` and `food_filtered_distance_cm`/`water_filtered_distance_cm`. Existing `food_distance_cm`/`water_distance_cm` remain filtered-distance aliases. Portable readings retain validity, freshness and sample timestamps. Acquisition is polling-based, not interrupt/RMT capture; timing accuracy and scheduler interactions require physical testing.
- The safety-input bridge rejects readings older than 2000 ms, nonfinite/out-of-range values and invalid RTC. The 2000 ms bound is a pre-hardware software choice, not a measured sensor specification.

## First real component: HX711

**None of the following physical steps has been executed.** Start only after the board/link gate, with HX711 + load cell as the first sensor.

1. **Verified ESP32-S3 board:** record exact board/module, memory configuration and serial route from physical identification; confirm the selected build matches it.
2. **Verified GPIO mapping:** review DOUT/SCK against that board and forbidden/reserved pins. Inject only those reviewed values with `M4_PINS_REVIEWED=1`; leave all actuator flags at 0.
3. **Voltage/power review:** confirm HX711 logic supply, ground, load-cell excitation and lead identification against the actual module. Power down for wiring.
4. **Connect HX711 only:** mechanically mount the load cell/platform; keep other sensors and servo/pump disconnected. Compile/upload the reviewed local HX711 image using the commands above; open the identified port at 115200.
5. **Raw readings:** inspect the mode/safety banner, `status`, and `avg 16`. Record raw counts, health and timeout/rail indications; absence of a factor must not produce grams.
6. **Stability:** repeat unloaded `avg 16` captures with timestamps and environment notes. Review drift/noise and mounting before calibrating; no acceptance threshold is invented here.
7. **Tare:** unload and stabilize, then `tare 16`. Confirm factor is unset, grams absent and status NOT_CALIBRATED.
8. **Known reference mass:** place an independently known reference mass with recorded value/provenance; stabilize and record the loaded raw average.
9. **Calibration factor:** send `cal <actual_reference_grams> 16` with the actual numeric mass substituted. Record the calculated signed factor; it is not yet an accuracy PASS.
10. **Validation masses:** remove/reapply the reference and other independently known masses; use `validate <actual_mass_grams> 16`. Record reference, measured value, absolute/relative error and unloading return separately.
11. **Repeatability:** repeat load/unload trials for each mass. Record every reading plus range/standard deviation if computed, environment and drift. Assign PASS/FAIL only against documented requirements chosen before acceptance; otherwise leave NOT_EVALUATED.
12. **Save evidence:** complete the blank worksheet in `SENSOR_CALIBRATION_RECORD.md`, preserve serial transcripts, mapping, factor, masses, notes and actual outcomes. Use `save YES` only for accepted measured calibration. No synthetic trial belongs in hardware evidence.

Follow-up **NVS test:** reboot after explicit save, inspect load result, then revalidate known masses. This is not completed persistence evidence. Retare/recalibrate if mounting/offset changes.

Follow-up **fault test:** safely power down/disconnect the module, then exercise missing readiness without live accidental shorts. Expected bounded TIMEOUT, invalid grams and no actuator output; explicitly restart an interrupted average after recovery. Record actual behavior, including failures. Only these real results can establish readiness.

Next components: explicit RTC read/set/retention and fault checks → each ultrasonic separately with measured full/empty geometry → OLED/button/active buzzer. Physical actuation is a later, separate electrical/mechanical task.
