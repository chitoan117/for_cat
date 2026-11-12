# ESP32-S3 current wiring / staged bring-up — 2026-10-21

## CURRENT authority — supersedes the historical V2 instructions below

Owner-selected **wiring declaration**, NOT a physically passed full assembly.
Board ESP32-S3,16MB flash,noPSRAM,2cores,240MHz; bridgeUART0,115200. Generic
DevKitC-1 manifest plus16MB overrides is a compile target, not the seller schematic.
Source `esp32/include/current_hardware.h`; machine mirror `config/hardware_current.json`.

| Role | GPIO | Runtime status in current safe sensor firmware |
|---|---|---|
| HX711 DOUT/SCK |4/5 | Dedicated `diag_hx711` opts in; raw/calibration before grams |
| Servo signal |6 | Wiring declared only, GPIO never configured/touched |
| Pump -> F5305S IN |7 | Wiring declared only, GPIO never configured/touched |
| OLED SDA/SCL |8/9 | SSD1306,0x3C owner-observed address |
| Optional bowl-water input |10 | RESERVED, installation unconfirmed, untouched |
| PIR HC-SR501 OUT |11 | Input-only observation in combined diagnostics; never feeds |
| HC-SR04 #1 approach TRIG/ECHO |12/13 | Separate ECHO3V3 acknowledgment before acquisition |
| JSN-SR04T #1 operational-water TRIG/ECHO |14/15 | Separate acknowledgment; actual controlled level placement TBDphysical |
| DS1302 CLK/DAT/CE |16/17/18 | Coherent RTC read, explicit set only |
| HC-SR04 #2 FOOD RESERVOIR TRIG/ECHO |TBD/TBD | Unassigned, no inventory reading/percent |
| JSN-SR04T #2 WATER RESERVOIR TRIG/ECHO |TBD/TBD | Unassigned, no inventory reading/percent |

`pins.h` is intentionally inert for the normal binary firmware; known wiring in
`current_hardware.h` is not permission to drive6/7. Sensor profile excludes6/7/10
even from generic PinIO. Old foodultrasonic6/7, water10/11, button12/buzzer13 are
retired. Do not flash old V2 combined images onto this new wiring.

### Candidate GPIOs — REPORT ONLY, require owner confirmation

Audit of source, Arduino `esp32s3` variant and generic board manifest found:

| Proposed future pair | Candidate TRIG / ECHO | Conditions before approval |
|---|---|---|
| HC-SR04 #2 |1 /2 | Not used by current map; confirm seller header/module wiring |
| JSN-SR04T #2 |21 /47 | Not used by current map; confirm both physically broken out/no onboard circuit |

These four numbers are NOT placed in canonical assignments or used at runtime.
Avoid0/3/45/46 straps,19/20nativeUSB,43/44UART0,39..42JTAG,26..38conservative
flash/PSRAM exclusions.22..25are not usable S3GPIOs. Generic variant defines onboard
RGB_LED48, so48is not proposed. Unknown seller-board/header routing prevents a
physical-safety guarantee from the generic SDK alone. Provide board photos/pinout
and confirm these candidates before adding #2 sensors. GPIO10remains reserved.

### Voltage / power

HC-SR04ECHO5V ->10k -> GPIO node ->20k ->GND gives about3.33V; verify actual
voltage at the GPIO side. Same for5VJSNECHO. Never direct5VECHO into3V3GPIO.
PIR/ultrasonics external5V as module-verified; HX711/OLED/DS1302 appropriate3V3.
External5Vmain has separate Jetson/ESP32VIN/servo/pump/F5305S/sensor branches.
Review common reference, polarity/current budget and USB/external5Vbackfeed before
simultaneous power. Servo/pump are not supplied from GPIO or Jetson dynamic-load rail.

## Implemented diagnostic scope (not full integrated control)

- `diag_hx711`:4/5only, `M4_HX711_INSTALLED=1` is a driver opt-in, not physicalPASS.
- `diag_all_sensors`:RTC/OLED/PIR/approach/operationalwater; HX opt-in remains0 by
  default until installation is deliberately selected. That image's NOT_INSTALLED
  weight reflects its disabled acquisition setting, not certainty about the newrig.
- `diag_approach_sensor`:mode4 on12/13. `diag_food_sensor` is a deprecated build-name
  alias to mode4, **not food hopper sensing**. Surrogate/legacy profiles remain
  compile regressions, not this board's physical deployment images.
- Current button/buzzer pins=-1, their old commands cannot reclaim12/13.
- Version2 ASCII JSON has `pin_contract=2026-10-21`, approachdistance/health/ack,
  PIRmotion/inputconfigured and rolesAPPROACH/WATER_OPERATIONAL. Legacy fooddistance/
  foodpercent and both inventorypercent fields staynull. Waterpercent is operational,
  never silently the reservoir quantity. No calibratednear threshold is fabricated.
- Calibration storage is `m4-calibration/sensors-v2`; old `sensors-v1` is preserved
  and NOT loaded into new channel roles. Re-tare/calibrate with the actual assembly.
  Binary calibration codec stays version1 internally; this new key scopes the wiring.
- Normal binary UARTv1 unchanged; GET_STATUS01meansalive, not sensorreadiness.
  ASCII monitor storesJSONL; automatic SQLite/API ingestion is a ROADMAP item.
- No FEED/SERVO/PUMP or manual-arm actuator driver exists here. All outputs0.
  Future benchmode must be defaultOFF/manualarm/expiry/bounded/stop-on-fault.

Current combined diagnostic commands (after actual voltage review, one sensor at a time):
```text
help
status
echo-approach-3v3 CONFIRM
echo-water-3v3 CONFIRM
approach-range ACTUAL_MIN_CM ACTUAL_MAX_CM
water-range ACTUAL_MIN_CM ACTUAL_MAX_CM
water-geometry ACTUAL_OPERATIONAL_FULL_CM ACTUAL_OPERATIONAL_EMPTY_CM
save YES
```
Placeholders are not numeric defaults to paste. `echo-food-*`, `food-range`,
`food-geometry` are rejected as legacy: #1 is approach, #2 hopper pins unassigned.
No inventorypercent before its own #2 calibration; operationalJSNblindzone must be
compatible with actual bowl/control geometry. Four-sensor scheduling remains TODO;
the current generic two-channel scheduler alternates with bounded timeout/quiettime.

## Next SINGLE physical test — isolated HX711 / food bowl

1. Disconnect servo/pump **power**. Wire HX7113V3/GND/DOUT4/SCK5 only, mechanically
   support the food bowl entirely on the load cell. Rim/chute must not touch chassis.
2. Build/flash **current `diag_hx711`**, not the old combined V2 image. Confirm
   actualchip/16MB/port; capture full raw serialtranscript.
3. Observe emptybowl/raw counts; `tare 16`. Place an independently known reference
   mass, then `cal ACTUAL_REFERENCE_GRAMS 16`.
4. After a new settled sample, `validate ACTUAL_REFERENCE_GRAMS 16`. Repeat known
   add/remove masses, including around40g, and record empty/load/unload drift/noise.
5. `save YES`, deliberate reboot, re-read and recheck known masses. No implicit
   tare/reference factor or physical tolerancePASS is assigned by the firmware.

Commands for the scale terminal:
```text
status
avg 16
tare 16
cal ACTUAL_REFERENCE_GRAMS 16
validate ACTUAL_REFERENCE_GRAMS 16
save YES
status
```
Only claim **PHYSICAL PASS** after actual reference/repeatability evidence and an
agreed acceptance tolerance. Current status remains PHYSICAL NOT TESTED.

## Exact HOST / Windows PowerShell commands

Current-source software validation:378Python,140safety+3351driverassertions,
6loopcases/142assertions/22reports,26processE2Ecases,7UARTvectors,40compileguards,
21firmwareprofilesPASS; UBSancanary/nativechecksPASS. This is HOST/SOFTWARE/COMPILE,
not physicalPASS. `checks_final` plus buildmanifest accompany the sensor-only handoff.
Prepared `diag_hx711`:app387232bytesSHA256
`ad67dd0c2a70835672cdbf24c3bcbf369c031dcdf8c0fb5c0f291582bf97f775`;
factory452768bytesSHA256
`71693b72dae84ba2195c460e71476c0bf0cb9083faef8d026249943e91836e6e`.
Image-info confirms ESP32-S3/16MB/checksum at file level, not actual board identity.

Actual working checkout for this audit (not `D:\for_cat` oldsnapshot):
```powershell
$Repo = 'C:\Users\chito\AppData\Local\Temp\opencode\for_cat_main_audit_full'
$Pio = 'D:\for_cat\.tools-venv\Scripts\pio.exe'
$Py = 'D:\for_cat\.venv\Scripts\python.exe'
& $Pio run --project-dir "$Repo\esp32" -e diag_hx711
& $Pio device list
```

Package into a NEW directory; packaging never flashes:
```powershell
$Bundle = 'D:\for_cat\ESP32_S3_HANDOFF_20261021_SENSOR_ONLY\deploy_hx711'
& $Py "$Repo\scripts\prepare_esp32_deploy.py" --env diag_hx711 --output $Bundle
$Manifest = Get-Content -Raw "$Bundle\deploy_manifest.json" | ConvertFrom-Json
$Manifest.files | Format-Table file,bytes,sha256
```
If bundle already exists, inspect/reuse its corresponding manifest or choose a new
path; do not overwrite history. Never reuse old V2 hashes for newimages.

**Future physical Windows flash, not executed by this task:** first close monitors,
review factory covered NVS/gaps/backups, inspect the observedport; do notguessCOM.
```powershell
$Port = Read-Host 'Observed ESP32-S3 COM port from device list'
$ToolPy = "$env:USERPROFILE\.platformio\penv\Scripts\python.exe"
$EspTool = "$env:USERPROFILE\.platformio\packages\tool-esptoolpy\esptool.py"
& $ToolPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub flash_id
# STOP unless actual output identifies the expected board and 16MB flash.
# Only after reviewing/accepting factory overwrite of covered sectors:
& $ToolPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub write_flash 0x0 "$Bundle\firmware.factory.bin"
& $ToolPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub verify_flash 0x0 "$Bundle\firmware.factory.bin"
& $Pio device monitor --port $Port --baud 115200
```
The existing PlatformIO `penv` successfully runs esptool5.3.0 on this host;
the separate `.tools-venv` Python lacks `rich_click` for that esptool package.
Use the exact interpreter above rather than installing into Nano/systemPython.
Application-only0x10000preservesNVS only when bootloader/partitions already match;
do not invent that precondition. No erase-all/stub retry/automatic actuator startup.

## Exact Jetson / MobaXterm commands (after reviewed source/bundle sync)

SSH is currently unreachable from the audit host. On Jetson localterminal get
`hostname -I`; use observedaddress in MobaXterm if mDNSfails. Review remoteGit before
any selective sync; the local changes have NOT been applied to Jetson in this task.
```sh
cd /home/toan/for_cat
git status --short
git branch --show-current
git log --oneline -5
PYTHONPATH=jetson python3 -B -m bringup.devices
ls -l /dev/serial/by-id/ /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```
Use an **observed** node and transferred matching bundle; no PlatformIO install or
build on Nano is necessary. The flashhelper works withPython3.6/existingesptool:
```sh
read -r -p 'Observed serial node: ' PORT
read -r -p 'Transferred deploy_hx711 directory: ' BUNDLE
SHA=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(next(x["sha256"] for x in d["files"] if x["file"]=="firmware.factory.bin"))' "$BUNDLE/deploy_manifest.json")
sh scripts/flash_esp32_from_jetson.sh --profile diag_hx711 --port "$PORT" --image "$BUNDLE/firmware.factory.bin" --sha256 "$SHA"
# Above is DRY RUN. Only after reviewed factory overwrite, actual board and power:
sh scripts/flash_esp32_from_jetson.sh --profile diag_hx711 --port "$PORT" --image "$BUNDLE/firmware.factory.bin" --sha256 "$SHA" --apply --allow-factory-overwrite
PYTHONPATH=jetson python3 -B -m bringup.sensor_monitor --device "$PORT" --seconds 30 --output /tmp/for_cat_hx711_NEW.jsonl
```
Monitor is read-only and exclusivefile; it sends no tare/calibration commands. Use
a serialterminal for explicit reference commands, close it before using themonitor.
Binarybackend/probe must not open the ASCIIimage's port concurrently.

Unchanged production detector smoke (no rebuild/replacement):
```sh
cd /home/toan/for_cat/jetson/ai
./cat_dog_trt --headless --no-snapshot --seconds 30
```

## Historical V2 checkpoint below — STALE PIN MAP / DO NOT FLASH ON NEW WIRING

Historical test counts, firmware hashes, absent-HX declaration and6/7/10/11/button/
buzzer instructions below describe the previousrig only. Preserve as provenance;
the current contract/commands above override them. V2 handoff remains archived,
not the release for current6servo/7pump/12approach/14water wiring.

**Current physical correction:** HX711/load cell is NOT INSTALLED; current
`diag_all_sensors` defaults to `M4_HX711_INSTALLED=0`, touches no scale GPIO and
reports `weight.quality=NOT_INSTALLED`, null grams. HX711 commands/procedures below
are future installed-component/software-fixture instructions. FOOD is currently
yellow/orange, WATER blue, one black cat. See `ESP32_STACK_V3.md` for current
bidirectional protocol/availability contracts. Earlier V2 evidence is historical.

**Current bundle is V2:** `D:\for_cat\ESP32_S3_HANDOFF_20261018_V2`. Real setup/loop
offline tests found/fixed cross-sensor HX711 calibration-state loss; see
`ESP32_S3_OFFLINE_VALIDATION.md`. Earlier images/hashes are superseded.

## Scope / provenance

User requested ESP32-S3 hardware integration after the camera/geometry milestone.
Starting Git checkpoint: `dff667d`. Existing Windows hardware work was inspected
before implementation: no-PSRAM16MB bridge profile, candidate sensor mapping and
DS1302 migration. Those changes were selectively restored into the current Git
checkout; the older Windows project, AI runtime and UART v1 codec were not replaced.

New `diag_all_sensors` compiles real sensor drivers together, prints human-readable
JSON at approximately1Hz and updates OLED. It is **ASCII_DIAGNOSTIC**, NOT the
normal binary UART v1 firmware. Normal `esp32s3_16mb_no_psram_hw_safe_uart` retains
PING/GET_STATUS/FEED_STATUS compatibility and disabled output policy; no new sensor
fields were inserted into frozen binary frames. Do not run the backend's binary
transport against an ASCII diagnostic image on the same serial node.

No MCU upload, live sensor acquisition, calibration accuracy or actuator motion
was performed. Neither Jetson nor Windows enumerated an ESP32 serial port during
this task. Candidate GPIOs below come from the existing agreed documentation;
their declaration/build success is not physical wiring verification.

## Board and candidate wiring

Current user-reported board: ESP32-S3,16MB flash, PSRAM not detected/used, USB bridge
to UART0 at115200. Official DevKitC compile manifest is a surrogate for the seller
PCB, with explicit16MB partition overrides; it does not certify its schematic.

| Peripheral | GPIO | Notes |
| --- | --- | --- |
| HX711 DOUT / SCK |4 /5 | Raw counts available; grams null until measured tare/reference calibration |
| Food ultrasonic TRIG / ECHO |6 /7 | ECHO must be shifted/divided to <=3.3V |
| OLED SDA / SCL |8 /9 | SSD1306 candidate0x3C,3.3V-compatible bus/pullups |
| Water ultrasonic TRIG / ECHO |10 /11 | Separate ECHO voltage/range review; module blind zone matters |
| Button |12 | INPUT_PULLUP, active LOW to GND; press reports intent only |
| Buzzer |13 | Disabled until existing active-high driver acknowledgment; passive tone not implemented |
| DS1302 CLK / DAT / CE |16 /17 /18 |3-wire, DAT bidirectional, RTC is NOT I2C |
| Servo / pump |UNASSIGNED | No PWM, MOSFET drive, automatic feed or refill |

Use common ground and correct module power/logic. Power off before wiring. Do not
connect a5V ECHO directly to an ESP32 GPIO. DS1302 supply/module battery circuitry
must be reviewed; firmware never enables its trickle charger. GPIO14/15 remain
unassigned, UART43/44 and native USB19/20 are not reassigned.

## Runtime behavior

- HX711 readiness/average/calibration reuses the bounded existing driver.
- DS1302 reads coherent bursts, checks CH/BCD/calendar, reports invalid/missing
  values as null, and only sets clock on explicit command with readback/WP restore.
- Two ultrasonic sensors have independent500ms minimum periods, at most one active
  acquisition,80ms post-acquisition quiet interval,30ms timeout. These timing/range
  defaults require physical validation, not a claim of calibrated accuracy.
- While echo edges are pending, loop avoids HX711/RTC/I2C/serial/report work.
  Trigger starts after other tasks/yield finish. Failures also respect retry budget.
- OLED64px shows sensor health, calibrated weight when available, FOOD/WATER
  distances and RTC UTC. Missing/stale readings show dashes, not invented values.
- Button logs `FEED_INTENT REJECTED SAFE_BUILD_ACTUATORS_DISABLED`.
- Water logic may expose `would_request_pump` for shadow policy only. Physical
  pump remainsfalse, actuator flag0; display/sensor success does not grant output.

Boot does NOT start ultrasonic acquisition or buzzer on candidate hardware. After
actual voltage/module/driver review, use separate human terminal commands:

```text
help
status
echo-food-3v3 CONFIRM
echo-water-3v3 CONFIRM
food-range MIN_CM MAX_CM
water-range MIN_CM MAX_CM
```

The CONFIRM strings acknowledge operator wiring review; they do not measure voltage.
Only send the relevant command after checking that sensor's actual ECHO circuit.
Minimum/maximum are measured/datasheet-supported module limits, not invented sizes.
Broad1..400cm sanity defaults are not a JSN blind-zone specification.

HX711, with properly mounted/unloaded bowl and actual known reference mass:

```text
avg 16
tare 16
cal ACTUAL_REFERENCE_GRAMS 16
validate ACTUAL_REFERENCE_GRAMS 16
save YES
```

Do not literally send the placeholder names. Raw average/calculated factor are
software results, not calibration PASS. Verify several masses/repeats before using
grams analytically. `save YES` stores sensor calibration in its existing separate
NVS namespace, not daily safety counters. No implicit tare or persistence on boot.

Level geometry uses actual full/empty sensor-to-surface measurements:

```text
food-geometry ACTUAL_FULL_CM ACTUAL_EMPTY_CM
water-geometry ACTUAL_FULL_CM ACTUAL_EMPTY_CM
save YES
load
```

Unknown geometry leaves percentage null. RTC uses explicit UTC2000–2099:

```text
set-utc YYYY-MM-DDTHH:MM:SSZ CONFIRM
```

Replace with actual reviewed UTC, then check readback and power/battery retention.
No boot/compiler-time clock reset. Buzzer requires a verified suitable active-high
driver: `buzzer-driver ACTIVE_HIGH CONFIRM`, then a bounded `buzz confirm`,
`buzz warning` or `buzz fault`. No servo/feed/pump commands exist in diagnostics.

## Build and prepared bundle

From the current checkout on a Windows host with the already-installed PlatformIO:

```powershell
pio run --project-dir .\esp32 -e diag_all_sensors
python -B scripts\prepare_esp32_deploy.py --env diag_all_sensors --output C:\absolute\NEW\bundle
```

Actual build host checkout used this session:
`C:\Users\chito\AppData\Local\Temp\opencode\for_cat_main_audit_full`.
Existing `D:\for_cat` was treated as historical user work and not overwritten.
Builds only, no `upload` target was used. Actual combined image:

| Product | Bytes | SHA256 |
| --- | ---: | --- |
| firmware.bin |394512 |`dd23d70c42e8d8f6665bf57a2bb7eca8d7337d10e11089e4c0164d997b8bca1b` |
| firmware.factory.bin |460048 |`2aebdfd404c54e90bf84a242f6070b5097f226ce65109bfa35d2fef0917cacfb` |

Actual app footprint387314B, static RAM25656B; these are compile/link metrics,
not measurements of heap, hardware behavior or sensor performance.
Prepared bundle on Windows:
`D:\for_cat\ESP32_S3_HANDOFF_20261018_V2\deploy`.
Manifest binds bootloader/partition/application/factory/boot_app0 products. Rebuilds
may change hashes; always use the corresponding new manifest.

## Jetson deployment / read-only monitor

After current source/bundle are synchronized and an ESP32 is physically connected,
inspect its actual Linux serial node. Existing flash helper supports the new profile.
Example DRY RUN, from repo root, replace BUNDLE and node with actual paths:

```sh
sh scripts/flash_esp32_from_jetson.sh \
  --profile diag_all_sensors --port /dev/ttyACM0 \
  --image "$BUNDLE/firmware.factory.bin" \
  --sha256 2aebdfd404c54e90bf84a242f6070b5097f226ce65109bfa35d2fef0917cacfb
```

This default performs no device IO/upload. Actual apply remains explicit, requires
ROM16MB preflight, no stub, no erase-all, SHA check and verify. Factory covered gaps
include NVS: do not apply without reviewing/backup; application-only at0x10000 is
appropriate only with already-matched16MB bootloader/partitions. No apply was run.

After deliberately flashing the matching ASCII image, close competing serial
monitors/backend transport, then use Nano Python3.6+ with existing pyserial:

```sh
PYTHONPATH=jetson python3 -B -m bringup.sensor_monitor \
  --device /dev/ttyACM0 --seconds 30 --output /tmp/NEW_sensor_samples.jsonl
```

Output file must be new. Monitor reads only; it sends zero serial commands, opens
no database, refuses enabled-output/nonfinite/invalid diagnostic reports, preserves
nulls and bounds each line4096bytes. Console summary/return code distinguish no
samples, rejected reports and oversized lines. Some USB bridges may reset on open.
Do not interpret a parsed report or `HEALTHY` driver status as physical milestone PASS.

## Executed verification

- Host full release checker PASS:362 Python tests,140 native safety assertions,
  3351 native driver assertions (3131 old +180 restored DS1302 +40 dual-scheduler),
  frozen UART7/7 vectors,34/34 compile guards,19/19 firmware build profiles.
- Final Python after three deploy-plan tests:365 PASS, Ruff changed Python PASS.
- V2 full release:365 Python,19 firmware profiles and previous safety/driver/guard
  checks PASS;6 actual setup/loop cases /131 assertions /21 decoded firmware
  reports PASS. Target ASan/UBSan/LSan also PASS; all hardware IO was mocked.
- Strict native `-Werror -Wconversion -Wsign-conversion -Wshadow` driver build PASS.
- Physical sensors, OLED panel, RTC retention, actual ECHO timing/voltage, HX711
  accuracy, buzzer, MCU upload and live serial readings: **NOT TESTED** in this task.

Host release logs:
`C:\Users\chito\AppData\Local\Temp\opencode\for_cat_esp32_checks_v2_20261018`.
Initial synchronization attempt was blocked by loss of Jetson SSH/mDNS reachability;
check the final session report for whether source transfer subsequently completed.
AI detector/model/camera source and binary, AI_SHADOW_MODE and binary UART v1 codec
remain protected. New code is not an authorization for actuator operation.
