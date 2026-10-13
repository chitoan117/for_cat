# M3 bring-up pack readiness — software preparation, milestone M2

Historical snapshot navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL pack-release snapshot, NOT CURRENT counts/driver availability:**170-test/five-build figures and absent-driver statements below record that release. Physical procedures/gates remain unpassed. Configured sensor/UI diagnostic foundations now exist; use `M4_DIAGNOSTIC_COMMANDS.md` for those builds and `CURRENT_PROJECT_STATE.md` for maturity. No active actuator image exists.

No physical test was run, no evidence log/photo was fabricated, no GPIO was assigned/enabled, no AI training/product feature was added and no completion score changed. `M3_HARDWARE_BRINGUP_MASTER.md` contains A–S prerequisites/connections/commands/expected/PASS/FAIL/safety/evidence/next gates. Exact transition definitions are in `M3_M4_GATE_DEFINITION.md`.

## Safe interface change and host checks

Existing S3 HW_SAFE uses **native USB CDC**, which is not the intended first CH343G path. Added separate **compile-surrogate-only** `esp32s3_n16r8_hw_safe_uart` (UART0, CDC-on-boot 0, actuator outputs 0, SIM absent), keeping all previous profiles. Optional once-only ASCII monitor banner reports firmware `0.1.0-m3-pack1`, build/board profile, actuator/simulation flags and `SAFE_BUILD_ACTUATORS_DISABLED`. Existing PING/GET_STATUS binary payloads/CRC/vectors stay unchanged. GET_STATUS byte 01 still says responsive, **not** build identity/sensor health. Original/native profiles have no new required banner.

The measured serial tool has `--m3 --json`: only PING/GET_STATUS, IDs, responses/payloads, correlation, CRC, RTT and timeout/failure state. First RTT may include USB-open/reset delay. No FEED_REQUEST flag/path was added because v1 cannot guarantee the image identity from status. Legacy explicit bad-CRC PING probe remains outside M3 mode; --m3 refuses --malformed.

Final Windows host `scripts/run_checks.ps1`: **170 Python tests PASS / 0 failed / 0 skipped** (all previous 163 retained), **140 native C++ assertions PASS**, **7 UART vectors PASS**, **5 compile guards PASS**, and **all 5** safe profiles compile. New bridge target: **RAM 22,740 / 327,680 B**, **flash 296,531 / 6,553,600 B**; original four footprints remain the RC2 values. PlatformIO Core 6.2.0 / Arduino 3.3.11 / platform 55.3.311; a Windows firmware-metrics/codepage notice still appears during linking, while actual size reports are printed. No upload or serial/camera probe occurred. Jetson diagnostic shell is prepared but unexecuted on real Jetson.

## Files created

- `docs/M3_HARDWARE_BRINGUP_MASTER.md`, `M3_M4_GATE_DEFINITION.md`, `M3_BRINGUP_PACK_READINESS.md`
- `docs/ESP32_S3_PC_DETECTION.md`, `ESP32_S3_BOARD_IDENTITY_CHECKLIST.md`, `ESP32_S3_FIRST_FLASH.md`
- `docs/GPIO_FINALIZATION_WORKSHEET.md`, `GPIO_VOLTAGE_PLAN.md`, `POWER_TREE_FINALIZATION_WORKSHEET.md`
- `docs/HX711_LOADCELL_BRINGUP.md`, `DS3231_BRINGUP.md`, `FOOD_LEVEL_SENSOR_BRINGUP.md`, `WATER_LEVEL_SENSOR_BRINGUP.md`
- `docs/OLED_BUZZER_BUTTON_BRINGUP.md`, `SERVO_BRINGUP.md`, `PUMP_BRINGUP.md`
- `scripts/m3_check_jetson.sh`, `esp32/include/build_info.h`, `jetson/tests/test_m3_pack.py`
- `evidence/README.md`, blank `.gitkeep` in jetson/webcam/esp32/serial/hx711/rtc/food_sensor/water_sensor/servo/pump directories

Modified: `.gitignore`, `esp32/platformio.ini`, `esp32/src/main.cpp`, `jetson/tools/test_serial.py`, `scripts/run_checks.ps1`, `scripts/run_checks.sh`, `docs/ESP32_S3_FIRST_DAY.md`, `docs/ESP32_S3_USB_SERIAL_OPTIONS.md`, `README.md`. No frozen API v1 or UART vector/codec change. Evidence paths are ignored except blank layout/instructions; no actual measurements exist there yet.

## Exact manual first commands

On Jetson, after board/supply review and boot alone:
```sh
cd "$HOME/forr_cat"
sh scripts/m3_check_jetson.sh
# ONLY if explicitly saving diagnostic output:
sh scripts/m3_check_jetson.sh --save
```

On PC at project root, after identifying the actual module and CH343G connector:
```powershell
$Pio = Join-Path (Get-Location) '.tools-venv\Scripts\pio.exe'
& .\.venv\Scripts\python.exe -m serial.tools.list_ports -v
& $Pio run -d esp32 -e esp32s3_n16r8_hw_safe_uart
# Only after module/memory/USB review and successful build:
$Port = 'COMx' # replace with observed port
& $Pio run -d esp32 -e esp32s3_n16r8_hw_safe_uart -t upload --upload-port $Port
& $Pio device monitor --port $Port --baud 115200
```
Record image hash and safe boot metadata; close monitor. From `jetson/` on PC: `..\.venv\Scripts\python.exe -m tools.test_serial --device COMx --m3 --count 3 --interval 1 --json`. This is PC evidence only.

On the real Jetson with its compatible isolated environment, discover actual `/dev/ttyUSB*` or `/dev/ttyACM*` then from `jetson/`: `python -m tools.test_serial --device ACTUAL_NODE --m3 --count 3 --interval 1 --json`. Record connected results, manually unplug and require failed/timeout/offline detection, reconnect/rediscover and repeat to prove recovery. Record UTC action times plus tool RTT; do not automate physical USB operations.

## Unresolved assumptions / later work

Seller board/module N16R8, WROOM-1/1U, antenna, dual connector routing, CH343G identity, actual capacities, supply and all GPIOs remain NOT VERIFIED. Jetson model/environment/package compatibility, physical flash/UART/reconnect and real component results remain NOT VERIFIED. M4 requires approved **real sensor/accessory/actuator test drivers and firmware**; current HW_SAFE cannot supply weight/distance/I2C reads or servo/pump motion. The plans explicitly say when no current executable exists. Do not treat a filled worksheet, banner, simulation or build as an M3/M4 physical PASS.
