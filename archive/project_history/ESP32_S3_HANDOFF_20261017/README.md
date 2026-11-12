# ESP32-S3 sensor firmware handoff — 2026-10-17

**SUPERSEDED:** use `D:\for_cat\ESP32_S3_HANDOFF_20261018_V2` for current source
and firmware. V2 fixes a cross-sensor calibration-state bug found by new actual-loop
offline tests. See `SUPERSEDED.md`; this directory is retained for history.

**UPDATE: Jetson reconnected and synchronization completed.** Exact staged source
tree and all firmware products were verified on `/home/toan/for_cat`; target native
ASan/UBSan checks passed. See `sync_receipt.json` for the current status. The
original `handoff_manifest.json` intentionally preserves the earlier offline state.
Jetson bundle: `/home/toan/for_cat/evidence/esp32_sensor_station_reconnect.BCqR4u/handoff/deploy`.
No upload/physical sensor validation was performed; ESP32 serial USB is not yet detected.

Firmware code and tests are complete for the current sensor-only integration.
This NEW directory preserves the result without overwriting the older Windows
project. Jetson SSH became unavailable before source synchronization; nothing was
flashed. Do not confuse build PASS with sensor/hardware PASS.

## Contents

- `source.zip`: exact staged ESP32 source, bring-up tools, tests and guide.
- `firmware_source.patch`: changes against current real-repo checkpoint `dff667d`.
- `deploy/`: built `diag_all_sensors` products and SHA256 deploy manifest.
- `checks/`: complete executed host release-check logs.
- `handoff_manifest.json`: source/archive hashes and build/validation scope.

Current Git working checkout on this PC:
`C:\Users\chito\AppData\Local\Temp\opencode\for_cat_main_audit_full`.
This handoff remains outside that temporary checkout so the work is preserved.

## Firmware

ESP32-S3 bridge UART0,115200,16MB flash, no PSRAM usage. New `diag_all_sensors`
reads HX7114/5, DS1302 CLK16/DAT17/CE18, OLED SDA8/SCL9, button12, and independently
reviewed food6/7 and water10/11 ultrasonic sensors. JSON once/sec, OLED health and
measurements. Buzzer13 stays inactive until explicit reviewed driver command.
Servo/pump remain unassigned and disabled; button never feeds.

Use source.zip's `docs/ESP32_S3_SENSOR_STATION.md` for actual wiring/calibration
commands. ECHO7/11 must never receive5V directly; each channel requires its own
review acknowledgment. Grams/percent stay null before measured calibration.

## Tests actually executed

- Final Python365 PASS.
- Native140 safety +3351 driver assertions PASS.
- Frozen UART vectors7/7 PASS; compile guards34/34 PASS.
- Safe firmware build matrix19/19 PASS.
- Strict native warnings-as-errors and changed Python Ruff PASS.
- Full release-check snapshot had362 tests; three deploy-plan tests were added
  afterward and the final full Python suite passed365. Firmware source unchanged.
- No board detected on Jetson or Windows; no upload or physical acquisition.

## Recover / build without Jetson

Extract source.zip into a NEW directory. From its root, on the PC with PlatformIO:

```powershell
pio run --project-dir .\esp32 -e diag_all_sensors
```

An already-built image is in deploy; do not upload until actual board/power/wiring
and serial route are confirmed. Factory flashing can overwrite NVS-covered gaps.

## Synchronize once Jetson is reachable

Transfer firmware_source.patch to Jetson. In `/home/toan/for_cat`, preserve local
work first, confirm starting checkpoint/source, then:

```sh
git apply --check /path/to/firmware_source.patch
git apply /path/to/firmware_source.patch
```

Patch is for `dff667d` real repo, NOT for applying over the old `D:\for_cat` snapshot.
No existing commits were rewritten, and no new hardware commit was made in this
task. Source remains staged in the working checkout for review.
