# ESP32-S3 sensor station V2 — preferred current handoff

**SYNC COMPLETE:** source and this V2 bundle were verified on Jetson. See
`sync_receipt.json`. Target bundle:
`/home/toan/for_cat/evidence/esp32_firmware_loop_v2.y29YQe/handoff_v2/deploy`.
No ESP32 was connected/opened/flashed for this offline validation.

This replaces the previous `ESP32_S3_HANDOFF_20261017` bundle. It fixes a real
cross-sensor calibration defect: setting FOOD/WATER geometry could reapply stale
HX711 calibration state and lose a new unsaved factor, or revive a pre-tare factor.
Successful tare/calibration now immediately synchronize the in-memory sensor
calibration record. No automatic NVS save or actuator authorization was added.

## Contents

- `deploy/`: current built diagnostic image and per-file SHA256 manifest.
- `source.zip`: current source, shared fake IO and offline firmware-loop tests.
- `firmware_source.patch`: complete changes from real-repo checkpoint `dff667d`.
- `firmware_increment_from_v1.patch`: update for the earlier staged V1 source tree.
- `checks/`: full executed host release logs, including firmware-loop evidence.
- `handoff_manifest.json`: exact source hashes, test counts and offline scope.
- `sync_receipt.json` when copied: actual subsequent Jetson synchronization record.

Firmware profile: `diag_all_sensors`, ESP32-S3 bridge/UART0,16MB flash, no PSRAM.
Hardware mapping is unchanged: HX7114/5, food6/7, OLED8/9, water10/11, button12,
buzzer13 (reviewed active-high driver only), DS1302CLK16/DAT17/CE18. Servo/pump
remain unassigned and disabled. ECHO input protection and measured calibration
remain necessary before actual sensor use. No ESP32 needs to be connected for
the tests below; no board was flashed or used to manufacture physical evidence.

## New end-to-end OFFLINE verification

The real `esp32/src/diagnostics.cpp` setup()/loop() executes in fresh host processes
with narrow fake Arduino GPIO/Wire/Preferences/Serial adapters. Firmware JSON is
then decoded by the real Jetson `bringup.sensor_monitor.parse_report` function.
This is NOT instruction-accurate ESP32/RTOS simulation or real timing validation.

Six named cases: missing sensors; HX711 calibration/NVS/cross-sensor state;
independent reviewed ultrasonic channels; missing/stuck echo and fault recovery;
RTC CH/write protection and malformed command recovery; button and bounded buzzer.
Results:6 cases,131 C++ assertions,21 received firmware reports PASS. No GPIO14/15
touches. All reports/artifacts are explicitly SYNTHETIC_FIRMWARE_LOOP.

Full host release:365 Python PASS,140 safety +3351 driver assertions,7 UART
vectors,34 compile guards,19 safe firmware builds. New full-loop tests are
reported separately, not inflated into the Python test count. Target Nano also
passed the full-loop matrix and native suites under ASan/UBSan/leak detection.

## Build / tests

Extract source.zip into a NEW directory. Build firmware with installed PlatformIO:

```powershell
pio run --project-dir .\esp32 -e diag_all_sensors
```

Offline loop test from the current checkout/extracted source (g++ example):

```sh
BUILD=$(mktemp -d /tmp/esp32-loop-offline.XXXXXX)
g++ -std=c++17 -O1 -Wall -Wextra -Wpedantic -Wshadow -Werror -Wno-unused-variable \
  -Iesp32/test/arduino_stub -Iesp32/include esp32/test/firmware_loop.cpp -o "$BUILD/firmware_loop"
python3 -B scripts/test_firmware_loop.py --binary "$BUILD/firmware_loop" --output "$BUILD/results"
```

Full-project checks additionally require the complete repository/dependencies;
`source.zip` intentionally packages sensor source, not the entire AI/backend tree.
Never add the host Arduino stub include directory to the actual PlatformIO build.

## Deployment status

Read sync_receipt.json for verified Jetson paths/source tree after transfer.
No upload, servo motion, pump operation, automatic feeding or physical sensor
accuracy test is implied by this bundle. Read `docs/ESP32_S3_SENSOR_STATION.md`
and `docs/ESP32_S3_OFFLINE_VALIDATION.md` in source.zip for exact procedures.
No new Git commit or push was requested/performed.
