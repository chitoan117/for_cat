# PHASE 1 PHYSICAL BRING-UP #1 — HX711 + load cell

**Current status: PHYSICAL NOT VERIFIED.** This runbook prepares the real test;
no serial measurements have been supplied and no board has been flashed by the agent.
Scope: HX711 only. Servo/pump power stays disconnected. CAT/DOG is unchanged;
no Web, tracker/FSM, arbiter or actuator implementation is part of this task.

This replaces the old statement that no HX711 tester exists. `diag_hx711` and all
required commands already exist and are reused. Old DS3231/assumed5kg/unspecified
pin wording is legacy; record the actual cell capacity/module instead of guessing.

## Existing implementation and compiled configuration

- `esp32/platformio.ini`: `diag_hx711`, S3/16MB/noPSRAM/UART0bridge,115200baud.
- `m4/hx711.h`: non-blocking readiness with500ms configured timeout, signed24bit
  raw acquisition, channelA/gain128, bounded1..64sample arithmetic mean, tare/cal.
- `m4/calibration.h`: tare/reference conversion, absolute/relative validationerror.
- `src/diagnostics.cpp`: commands below; async results printed after Nnew samples.
- `m4/arduino_io.h`, `calibration_record.h`: checked calibrationcodec and explicit
  NVSsave/load, namespace `m4-calibration`, current key `sensors-v2`.
- GPIO DOUT=4/SCK=5. Mode1 initializes HX711, not RTC/OLED/PIR/ultrasonic sensors.
  UART0bridge transport is separate; do not move to nativeUSB or remap pins here.
- `ACTUATOR_OUTPUTS_ENABLED=0`, `SERVO_DIAGNOSTIC_ENABLED=0`,
  `PUMP_DIAGNOSTIC_ENABLED=0`; actuatorinterfaces remain disabled/noGPIO.

Preparation is at `D:\for_cat\HX711_PHYSICAL_BRINGUP_20261021_PREP`:
fresh COMPILE PASS, resolvedflags, compiledheaderprobe(DOUT4/SCK5/mode1/output0),
imageinfo and matching deploymanifest. App387232bytes; RAM25656bytes/linkflash380434.
These are software/config/file checks, NOT physical evidence.

## Wiring and mounting

| HX711 | ESP32-S3 |
|---|---|
| VCC |3V3 |
| GND |GND |
| DOUT/DT |GPIO4 |
| SCK/CLK |GPIO5 |

Identify load-cell excitation/signal connections using the actual module/cell
labels/diagram; do not infer E+/E-/A+/A- from wirecolor alone. Record mounting and
cellcapacity. Keep the movable measuring platform clear of chassis/chute contact
and cable tension. The foodbowl is later mounted on this platform; changing the
mechanical/tare configuration requires a new tare/calibration test.

## Build — Windows PowerShell

The working source is the Gitmirror below, not the old `D:\for_cat` source snapshot.
```powershell
$Repo = 'C:\Users\chito\AppData\Local\Temp\opencode\for_cat_main_audit_full'
$Pio = 'D:\for_cat\.tools-venv\Scripts\pio.exe'
$Evidence = 'D:\for_cat\HX711_PHYSICAL_BRINGUP_20261021_PREP'
$Bundle = "$Evidence\deploy_hx711"
& $Pio run --project-dir "$Repo\esp32" -e diag_hx711
& $Pio device list
```
The agent's enumeration returned no ports; choose the actual observed COM after
connecting your board. No COM number is assumed.

## Flash — only after chip/16MB/hash and covered-range review

Current prepared factory SHA256:
`71693b72dae84ba2195c460e71476c0bf0cb9083faef8d026249943e91836e6e`.
Factory writes cover bootloader/partitions/application and NVS/gaps: review/backup
existing calibration/settings before initial flash. No erase-all/stub workaround.
```powershell
$Port = Read-Host 'Observed ESP32-S3 COM port'
$FlashPy = "$env:USERPROFILE\.platformio\penv\Scripts\python.exe"
$EspTool = "$env:USERPROFILE\.platformio\packages\tool-esptoolpy\esptool.py"
$Image = "$Bundle\firmware.factory.bin"
$ExpectedHash = '71693b72dae84ba2195c460e71476c0bf0cb9083faef8d026249943e91836e6e'
if ((Get-FileHash -LiteralPath $Image -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedHash) { throw 'Firmware SHA256 mismatch' }
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub flash-id
if ($LASTEXITCODE -ne 0) { throw 'ROM preflight failed; stop' }
```
STOP if chip/flash size differ or the command fails. After confirming the expected
ESP32-S3/16MB and accepting the reviewed factorywrite, run:
```powershell
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub write-flash 0x0 $Image
if ($LASTEXITCODE -ne 0) { throw 'Flash failed; stop' }
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub verify-flash 0x0 $Image
if ($LASTEXITCODE -ne 0) { throw 'Verify failed; stop' }
```
PlatformIOpenv's existing esptool5.3.0 was verified to run; the separate toolsvenv
Python lacks rich_click for this package. Do not install/upgrade runtimes for this.

## Monitor / record output

Close competing monitors/backend readers. The following is interactive115200baud;
type **one command then wait for its result** before entering the next. Starting
another avg/tare/cal/validate while one is collecting replaces the pending action.
```powershell
Push-Location $Evidence
try {
    & $Pio device monitor --port $Port --baud 115200 --eol LF --echo --dtr 0 --rts 0 --filter send_on_enter --filter log2file
} finally {
    Pop-Location
}
```
The installed log2file filter prints the actual logfile path under `$Evidence\logs`.
It records received firmware output, not a guaranteed full TXcommand transcript;
keep a short note of command order and reference masses too. Ctrl+C closes monitor.
If bootbanner was missed, openmonitor then press EN/RST; do not infer failure from
a missing banner alone. Bridge opening may still reset some boards.

## STEP A — EMPTY SCALE

Keep the measuring platform empty, with no reference object/food. Record whether
a bowl/platform is already part of the tare assembly; do not change it mid-test.
After initial conversions are available, type:
```text
status
tare 16
```
Check finite `raw_counts` and no repeated TIMEOUT. A connected but uncalibrated
scale normally reports `weight_health=NOT_CALIBRATED`, `grams=null`; HEALTHY is not
required before calibration. First-use NVSload0(MISSING) is not a sensorfault.
Wait for `AVERAGE raw=...` then `TARE_CAPTURED factor remains NOT_CALIBRATED`.

## STEP B — ZERO STABILITY

Without touching/re-taring the scale, type `avg 16` repeatedly; wait for each
`AVERAGE raw=...` before the next. Preserve the intervening1Hz statusreports.
```text
avg 16
```
Record all means/drift/raw fluctuations and any timeout. **avg reports rawcounts,
not grams**. Tare clears the oldfactor intentionally, so grams staynull until STEP C.
Arithmetic averaging does not certify stability; no acceptable noise threshold is
invented. We will characterize spread/drift from real output before tuning.

## STEP C — CALIBRATION

Place a mass known from an actual reference, wait for mechanicalsettling, then:
```text
cal ACTUAL_REFERENCE_GRAMS 16
```
Replace the placeholder by the measured mass. `cal 100.0 16` is correct ONLY if
the actual reference is100.0g; no100gdefault is used. Wait for `AVERAGE raw=...`
and `CALIBRATION result=CALCULATED grams_per_count=... NOT_HARDWARE_VERIFIED`.
Factor can be negative if cellsignal polarity produces decreasing rawcounts under
load; sign alone is not a failed calibration. A new ADCsample is needed aftercal.

## STEP D — VALIDATION

With the known mass on the same setup:
```text
validate ACTUAL_REFERENCE_GRAMS 16
status
```
Wait for `VALIDATION measured=... reference=... absolute_error=... relative_percent=... PASS_TOLERANCE_NOT_ASSIGNED`.
Record measured/reference/error, not only `CALCULATED`. Remove/reapply the same
known mass and repeat validation; if another independently known mass is available,
record that too. Repeating the calibration mass alone is not a full linearity test.

Also check the unloaded condition WITHOUT newtare. Current operational grams
conversion rejects negative results: a small below-tare fluctuation can show
`grams=null`/`DEGRADED INVALID_DATA`, rather than a negativegramvalue. Preserve its
rawcounts and the taremean/factor; do not silently call it zero, hide it by repeated
tare, or confuse it with `NOT_CONNECTED TIMEOUT`. This behavior is reported as-is;
no driver/physical-noise tuning is made without measurements.

## STEP E — PERSIST / REBOOT

Only after calibration/validation look reasonable:
```text
save YES
```
Expected `CALIBRATION_SAVED not safety counters`. Then press EN/RST or perform a
deliberate boardpowercycle. **Do not reflash, tare, or calibrate again** before
checking persistence; keep/reapply the known mass in the unchanged assembly.
```text
status
validate ACTUAL_REFERENCE_GRAMS 16
```
Expected boot `CALIBRATION_LOAD code=2`(LOADED), then a fresh validweight and repeat
validation. Immediate bootINITIALIZING/null before a newconversion is not itself
persistencefailure. Load0=MISSING,1=INVALID,2=LOADED; report other outcomes verbatim.

## Command outcomes / fault meanings

| Command | Expected actual firmware text/fields |
|---|---|
| `status` | JSONmode=diag_hx711, raw_counts/grams/weight_health/reason, actuator_outputs_enabled=0, physical_pump_on=false |
| `avg N` | `AVERAGE raw=...` after Nnew samples |
| `tare N` | `AVERAGE raw=...`, `TARE_CAPTURED factor remains NOT_CALIBRATED` |
| `cal G N` | `AVERAGE raw=...`, `CALIBRATION result=CALCULATED grams_per_count=... NOT_HARDWARE_VERIFIED` |
| `validate G N` | validation measured/reference/absoluteerror/relativepercent, no automatic tolerancePASS |
| `save YES` | `CALIBRATION_SAVED not safety counters` |
| collectionfault | `AVERAGE_ABORTED SENSOR_FAULT_OR_TIMEOUT`; check health/reason |

Nmustbe1..64; Grealpositivefinite. Invalid/inactive requests may return
`REJECTED CONFIGURATION_INVALID`, `INVALID_CALIBRATION`, `INVALID_REFERENCE`;
invalidfactor/reference may yield `CALIBRATION result=INVALID` or
`VALIDATION NOT_CALIBRATED_OR_INVALID`. Savefailure is
`REJECTED NOT_CALIBRATED_OR_NVS_ERROR`. RawADCrails may produceFAULT/INVALID_DATA.
No command returns a legitimate physicalPASS certificate.

## PASS / FAIL / evidence

PHYSICALPASS requires actual evidence of communication, tare, usablezero stability,
knownmasscalibration, acceptable repeatvalidation, persistence afterreboot and no
abnormaltimeouts/faults. Noise/accuracy acceptance tolerances are **not assigned**
by this task; record actualresults and agree tuning/acceptance from evidence.
Until reviewed evidence exists, all physicaltestitems remain PHYSICAL NOT VERIFIED.

FAIL evidence includes repeatedtimeouts, ADCrails, unusablestability, knownmass
error beyond the agreed limit, calibration/persistence failure or invalid readings
reported as if they were valid. A correctly rejected badcommand is not by itself
a failed loadcell. Mechanicalcontact/cableforce invalidates the weighing setup.

Send back: fullreceived seriallog including boot and reboot, commandorder,
exactreference mass+howestablished, cellcapacity/module/rate ifknown, wiring/mount
photos, unloaded repeats and remove/reapply validations, and anyerror verbatim.
Use `physical_observations_TEMPLATE.md` in the preparationfolder; no fakevalues.
Copy that template to a new actual-observations file before filling it; keep the
published template and pre-test manifests unchanged.
The agent will compare the actual readings before deciding PASS/tuning/follow-up.
