# GPIO21 diagnostic validation / handoff — 2026-10-23

## Completed checks

- Current firmware loop under UBSan:5 cases,77 assertions,20 Jetson-parsed reports PASS.
- Cases: missing sensors, functional sensors, sensor faults, button bounce/hold/
  millis rollover/concurrent echoes, held-at-boot inhibit.
- No GPIO6/7/10 touches, no LEDC attachment/write, no NVS write in host cases.
- Existing native drivers:3351 assertions PASS under UBSan.
- Compile guards:69/69 PASS.
- Focused Python current-hardware/weight physical-contract tests:13/13 PASS.
- git diff --check PASS. No full build matrix or new ASan result claimed.
- PlatformIO diag_current_hardware build PASS; app397936 bytes, RAM25768,
  link flash390746. Manifest: deploy/deploy_manifest.json.

## Actual deployment / boot

- COM8 CH343 serial5C85066678 confirmed; user explicitly confirmed monitors closed
  and servo/pump physical power OFF before deployment.
- ROM ESP32-S3,16MB flash, embedded8MBPSRAM observed; firmware does not use PSRAM.
- physical_flash/stages.json: base and prior app match, app-only0x10000 write,
  app verification PASS; no factory/partition/NVS write. NVS20KiB before/after
  identical, SHA25642ec58a3638e84a41138331bb5069e5730ca75f7aba86b3ac4468023269d787e.
- New installed app SHA256118bfb14cb8adc3fe435857c5dc463cad4874552bba072bab482584158c326a1.
- Preflight raw serial: D:\for_cat\CURRENT_HARDWARE_DIAGNOSTIC_20261022\physical_runs\20261023_BUTTON_GPIO21_PREFLIGHT_13
- Post-flash raw serial: D:\for_cat\CURRENT_HARDWARE_DIAGNOSTIC_20261022\physical_runs\20261023_BUTTON_GPIO21_BOOT_14
-14 parsed post-flash reports: mode correct, OLED HEALTHY/initialized, PIR
  configured, HX raw available/gram calibration absent, button HIGH/HIGH/released/
  HEALTHY/count0, arms/AUTO flags false/output0. No reset/brownout loop observed
  in the bounded window. The assistant's serial session is closed.
- Echo ACK flags reset false on reboot by existing design; sensors were not
  re-enabled or physically re-tested during button boot verification.

## Exact repository files changed for this task

```text
esp32/include/m4/accessories.h
esp32/include/m4/candidate_sensor_pins.h
esp32/src/diagnostics.cpp
esp32/test/arduino_stub/Arduino.h
esp32/test/current_hardware_loop.cpp
scripts/test_current_hardware_loop.py
scripts/check_release.py
config/hardware_current.json
docs/MANUAL_BUTTON_BRINGUP.md
docs/CANONICAL_HARDWARE_STATE_20261023.md
docs/CURRENT_PROJECT_STATE.md
docs/CURRENT_HARDWARE_DIAGNOSTIC.md
docs/ROADMAP.md
docs/ESP32_S3_SENSOR_STATION.md
docs/PIN_ARCHITECTURE.md
docs/HARDWARE.md
docs/HX711_LOADCELL_BRINGUP.md
docs/SERVO_BRINGUP.md
docs/CLOSED_LOOP_DISPENSE_BRINGUP.md
README.md
JETSON_COMMANDS.md
```

External deployment helper created:
C:\Users\chito\AppData\Local\Temp\opencode\deploy_gpio21_diagnostic_20261023.py

Evidence outputs generated only in this new evidence directory and the named
serial-run subdirectories (the denied-open attempt is retained in
20261023_BUTTON_GPIO21_PREFLIGHT_12). Original firmware release was not overwritten.

## Stop condition

GPIO21 diagnostic/software/flash/boot ready; **BUTTON PHYSICAL NOT YET VERIFIED**.
Exact user sequence in repository docs/MANUAL_BUTTON_BRINGUP.md: released N,
brief press N+1, release unchanged, second press/hold3–5s N+2 with no repeats,
release unchanged, final new press N+3. No actuator execution. Wait for actual
user switch/debounce/hold evidence; do not proceed to dispensing or pump.
