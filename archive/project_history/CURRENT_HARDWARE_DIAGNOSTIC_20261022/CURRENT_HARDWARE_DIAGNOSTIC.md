# Phase1 — CURRENT physically wired hardware: staged diagnostics

**Owner-reported WIRED, NOT PHYSICALLY VERIFIED in this task.** The two reservoir
sensors HC-SR04#2 and JSN-SR04T#2 are **NOT WIRED**; their GPIOs remain TBD and
their missing readings do not fail the current profile. The camera/Jetson CAT/DOG
production program is preserved; none of these diagnostic images connects AI,
MealPlan, Web, automatic feed or autonomous water refill to actuator GPIOs.
Jetson SSH is currently reachable; read-only inventory listed `/dev/ttyACM0`
("USB Single Serial", VID6790/PID21971), but **did not open the node or identify
the attached MCU**. Remote Git `main/dff667d` retains36 V2 staged files and an
untracked detector backup; current diagnostic source/bundle was built on the
Windows Gitmirror `main/ac17065` and is NOT yet deployed to Jetson. Verify
actual ROM chip/16MB/serial node before any operator flash; do not overwrite
remote staged work to "sync" it blindly.

## What exists (one block at a time)

| Profile | Purpose | Servo6 | Pump7 |
|---|---|---|---|
| `diag_current_hardware` | OLED0x3C, DS1302, PIR, HX4/5, approach12/13, operationalwater14/15 | NOT TOUCHED | NOT TOUCHED |
| `diag_servo_bench` | Standalone manual-arm, bounded PWM, provisional CLOSE/OPEN | CAN MOVE AFTER ARM | NOT TOUCHED |
| `diag_pump_bench` | Unknown F5305S polarity: read-only/inert command test | NOT TOUCHED | NOT TOUCHED |
| `diag_pump_bench_active_high` | Manual-arm pump after active-HIGH and boot-OFF verified | NOT TOUCHED | OFF level0 / ON level1 |
| `diag_pump_bench_active_low` | Manual-arm pump after active-LOW and boot-OFF verified | NOT TOUCHED | OFF level1 / ON level0 |

**Do not choose high/low based on a guess.** Compiling either variant only proves
the circuit logic can build, not what the real F5305S IN signal does. An externally
powered F5305S can switch during ESP32 reset/boot before firmware takes control.
Pump power must remain disconnected until the actual module's OFF polarity,
pull/bias during reset and shared ground are measured. A controller cannot prove
OFF with status JSON alone; if boot-off bias is wrong, STOP and correct hardware.
There is no current image that drives both servo and pump simultaneously.

`diag_current_hardware` combines the already-existing DS1302/OLED/HX/ultrasonic
drivers and PIR GPIO11. **It does NOT read servo/pump physical position/current**:
reported servo `PWM_NOT_ATTACHED_CLOSE_PHYSICAL_UNVERIFIED` and pump
`OUTPUT_NOT_ENABLED_PHYSICAL_OFF_UNVERIFIED` describe commands, not measured gates.
The sensor-only image never drives GPIO6/7. Do not energize actuator power during
steps1–7, even if those loads are mechanically wired to the feeder.

## Machine-readable `status` in current sensor image

Current ASCII JSON approximately1Hz and on manual `status` reports:

- `rtc_health`, `rtc_utc` (if valid), `current_hardware.rtc_detected`.
- `oled_health`, `current_hardware.oled_initialized`, `oled_address="0x3c"`.
- `motion` true/false and `pir_transition_count`, `pir_last_transition_ms` (null
  until an actual change after boot). PIR does not identify CAT/DOG.
- `raw_counts`, `grams` (null until valid factor), `weight.health/quality`,
  `weight_calibrated`, four NEW sample window, measured window range, and
  `weight_stable`. Stability is **null until the operator explicitly configures a
  measured tolerance**: `weight-stability ACTUAL_MAX_RANGE_G CONFIRM`.
  Config range must be finite >0..10g as a software input cap, not a physical
  acceptance threshold. A valid0g is not unavailable; negative near-tare grams
  may be null by the HX driver and must not be silently called zero.
- `approach_distance_cm`, `approach_distance_valid`, `approach_health`,
  `approach_timeout_count`; equivalent operational water fields including
  `operational_water_timeout_count`. Ultrasonic counters start at0 and reset if
  that channel is reconfigured/restarted. Raw distance can exist while water%
  remains null before measured FULL/EMPTY geometry.
- `food_reservoir_sensor="NOT_WIRED"`, `water_reservoir_sensor="NOT_WIRED"` and
  percentages null; never feed fake inventory or mark absence as FAULT.
- `servo_armed=false`, `pump_armed=false`, `auto_feed=false`, `auto_water=false`,
  `actuator_outputs_enabled=0`, `hardware_verified=false`. Never interpret a
  reported HEALTHY driver as physical PASS without a real operator test.

**Ultrasonic Echo protection:** HC#1 GPIO13 and JSN#1 GPIO15 must be checked at
the GPIO side of a suitable level divider; never connect a5V Echo directly to
ESP32. Separate `echo-approach-3v3 CONFIRM` / `echo-water-3v3 CONFIRM` commands
enable only that sensor **after electrical review**; a typed CONFIRM is not a
voltmeter result. GPIO10 remains reserved/unconfirmed; no reservoir GPIO assigned.

## Build and physical flash — current sensor-only profile

Source is the audited Windows Gitmirror; `D:\for_cat` remains a separate old
snapshot/data/handoff tree. On the Windows host:
```powershell
$Repo = 'C:\Users\chito\AppData\Local\Temp\opencode\for_cat_main_audit_full'
$Pio = 'D:\for_cat\.tools-venv\Scripts\pio.exe'
$Py = 'D:\for_cat\.venv\Scripts\python.exe'
$Bundle = 'D:\for_cat\CURRENT_HARDWARE_DIAGNOSTIC_20261022\deploy'
& $Pio run --project-dir "$Repo\esp32" -e diag_current_hardware
& $Pio device list
# Only if creating a NEW bundle; do not overwrite an existing release:
# & $Py "$Repo\scripts\prepare_esp32_deploy.py" --env diag_current_hardware --output $Bundle
```

The deploy manifest binds app/factory/bootloader/partition hashes. A **factory
image can overwrite NVS**, including the previously calibrated loadcell. Prefer
application-only at0x10000 if the board's installed bootloader and partitions
match the bundle, using actual readback verification first. Do not blindly flash
an old HX/servo image on current wiring. Physical build/flash commands below are
instructions, **not actions performed in this audit**.
The generic bundle manifest still contains `flash_image=firmware.factory.bin` as
the full first-install option; it is **NOT an instruction to run factoryflash
after scale calibration**. The commands here deliberately use `firmware.bin`.

```powershell
$Port = Read-Host 'Observed ESP32-S3 COM port'
$FlashPy = "$env:USERPROFILE\.platformio\penv\Scripts\python.exe"
$EspTool = "$env:USERPROFILE\.platformio\packages\tool-esptoolpy\esptool.py"
$Manifest = Get-Content -Raw "$Bundle\deploy_manifest.json" | ConvertFrom-Json
$Expected = ($Manifest.files | Where-Object file -eq 'firmware.bin').sha256
$Image = "$Bundle\firmware.bin"
if (-not $Expected -or (Get-FileHash -LiteralPath $Image -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Expected) { throw 'Wrong firmware SHA' }
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub flash-id
if ($LASTEXITCODE -ne 0) { throw 'ROM chip/flash preflight failed' }
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub verify-flash 0x0 "$Bundle\bootloader.bin" 0x8000 "$Bundle\partitions.bin"
if ($LASTEXITCODE -ne 0) { throw 'Actual bootloader/partitions mismatch: STOP without flashing' }
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub write-flash 0x10000 $Image
if ($LASTEXITCODE -ne 0) { throw 'App-only flash failed' }
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub verify-flash 0x10000 $Image
if ($LASTEXITCODE -ne 0) { throw 'App verify failed' }
```

If the board has no matching base image, STOP and review backup/partition plan
before any *deliberately approved* factory flash. Do not erase-all to fix a
mismatch. Unplug servo/pump power for this sensor-only image. Start monitor after
flash/reboot; the program is ASCII, not the Jetson binaryUARTv1 image:
```powershell
Push-Location 'D:\for_cat\CURRENT_HARDWARE_DIAGNOSTIC_20261022'
try {
    & $Pio device monitor --port $Port --baud 115200 --eol LF --echo --dtr 0 --rts 0 --filter send_on_enter --filter log2file
} finally { Pop-Location }
```
The installed log2file filter saves received text under `logs/`; note typed
command order yourself. Close all other monitors before switching profiles.

## Ordered supervised tests, **never both actuators together**

1. **ESP32 boot:** servo/pump power disconnected. `status`, keep serial monitor
   running to observe reboot loop/brownout/watchdog warnings. No unexpected
   physical movement with independent power later. `hardware_verified=false`
   does not become PASS merely from surviving boot.
2. **OLED:** `status` -> `oled_health`, address0x3C and display changes. Verify
   actual text/panel with eyes; I2C ACK alone is not screen qualityPASS.
3. **DS1302:** `status` -> RTC health/UTC; compare to a real reference. If stopped,
   only after actual UTC is known: `set-utc YYYY-MM-DDTHH:MM:SSZ CONFIRM`, read
   back, powercycle later and check retention. No boot-time clock write.
4. **PIR:** stand still, `status`, move in sensing field, `status`, leave and wait
   the module's own reset delay, `status`. Record true/false, transition counter/
   last timestamp. PIR is not CAT detection and never triggers feed.
5. **HX711:** `status`, `avg 16` repeatedly, `tare 16` only with empty bowl and
   explicit intent. If already physically calibrated and saved, *do not retare*
   just for monitoring: use `validate ACTUAL_REFERENCE_GRAMS 16`. Unknown factor
   means `grams:null`; new known-weight calibration via `cal ACTUAL_REFERENCE_GRAMS
   16`, `save YES` only after validation. Configure `weight-stability REAL_MAX_RANGE_G
   CONFIRM` from measured noise, then record four-sample range and stable flag.
6. **HC-SR04#1 approach:** inspect GPIO13 divider at <=3.3V then type
   `echo-approach-3v3 CONFIRM`. Test with independently measured near/mid/far
   distances, `status` each. Record raw/filteredcm/validity/timeouts. **No feed.**
7. **JSN-SR04T#1 operationalwater:** inspect GPIO15 divider, then
   `echo-water-3v3 CONFIRM`. Record actual low/normal/desiredtarget distances
   and blindzone. Percent remains null until real water FULL/EMPTY geometry is
   intentionally set with `water-geometry REAL_FULL_CM REAL_EMPTY_CM`.
   Pump stays OFF; `would_request_pump` is only shadow-policy telemetry.
8. **Servo:** close sensor monitor; use separate `diag_servo_bench` after physical
   prerequisites in `SERVO_BRINGUP.md`. It is default disarmed, manually arm,
   tiny unloaded OPEN then CLOSE, disarm. Pump branch remains unpowered. Recording
   a CLOSE *command* is not mechanical closure evidence.
9. **Pump/F5305S:** close servo monitor, unpower servo branch. Start with inert
   `diag_pump_bench`: `pump status`, `pump arm YES` rejected, `pump on 50`
   rejected; it never configures GPIO7. Determine actual module IN active polarity
   and boot/reset OFF bias electrically **with pump5V disconnected**. Only then
   choose ONE active_high or active_low profile, verified app-only flash and a
   short supervised `pump arm YES` → `pump on 50` → automaticOFF → `pump off`
   → `pump disarm`. `50` milliseconds is an INITIAL bounded pulse example, not
   proof of useful flow. GPIO7 to F5305S IN, **never** drive motor fromGPIO;
   monitor actual5V supply, ESP32 reset/brownout, motor current/flow, and stop.

The pump active profile does not sample other sensors concurrently. Record power
rail behavior during the pulse and rerun sensor-only status afterward; combined
real sensor accuracy during pump operation needs a separate validated test.

## Guarded pump profile selection — NO DEFAULT ACTIVE POLARITY

The active-high and active-low builds exist for code validation, **not permission
to flash either on an unverified F5305S**. Pick exactly one only after proving
OFF input level and boot/reset bias with the exact module. Do not swap binaries
blindly to discover polarity. No external pull/bias or power-loss interlock is
certified by software. The canonical inert `diag_pump_bench` cannot driveGPIO7.
When chosen, build the *reviewed* named environment and inspect its current hash;
application-only update requires the same on-board base-image check as above.
```powershell
# Replace the variable ONLY after actual module polarity measurement:
$PumpProfile = Read-Host 'Verified profile: diag_pump_bench_active_high OR diag_pump_bench_active_low'
if ($PumpProfile -notin @('diag_pump_bench_active_high','diag_pump_bench_active_low')) { throw 'Unknown reviewed pump profile' }
& $Pio run --project-dir "$Repo\esp32" -e $PumpProfile
$PumpImage = "$Repo\esp32\.pio\build\$PumpProfile\firmware.bin"
Get-FileHash -LiteralPath $PumpImage -Algorithm SHA256
# Verify actual installed bootloader/partitions and board again before app-only
# flash at 0x10000; preserve calibrated HX NVS and logs.
```
After approval of actual module polarity, the `write-flash`/`verify-flash`
commands above apply with `$Image=$PumpImage` and the reviewed hash. The
`diag_pump_bench` inert build is appropriate until that evidence exists.

## Physical classification / evidence to send

For each step send complete serial RX log + typed command order, board/model,
firmware hash and power wiring, photo/video, measured distances/weights/water
levels/reference values and actual sensor voltage. For pump include F5305S
module IN polarity, OFF bias under reset, ON/OFF motor behavior, 5V voltage,
current/flow if measured, and resets/jitter. For servo include calibrated CLOSE/
OPENus and mechanism observations. Keep distinct statuses:

- User says components1..12 above are **WIRED**, but no new integrated measurement
  log has been supplied: **PHYSICAL NOT VERIFIED / READY FOR PHYSICAL TEST**.
- HC-SR04#2/JSN-SR04T#2 are **NOT WIRED** and not required for this sequence.
- HOST TEST/COMPILE PASS is never a sensor/servo/pump PHYSICAL PASS.
- `pump_state=OUTPUT_NOT_ENABLED_PHYSICAL_OFF_UNVERIFIED` is *not* a measured OFF
  state of externally powered pump. If an input pulls active at boot, unplug
  motor power and stop rather than declaring this diagnostic safe.
