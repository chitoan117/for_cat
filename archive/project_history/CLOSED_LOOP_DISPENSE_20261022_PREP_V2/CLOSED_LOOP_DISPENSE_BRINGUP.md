# Phase1 #3 — supervised Servo + HX711 closed-loop bench

**PHYSICAL NOT VERIFIED.** This runbook documents an explicit manually armed
diagnostic; it is not CAT auto feed, MealPlan, FeedNow, production servo, pump
control or proof of ~40g precision. Production CAT/DOG C++ was not modified.

## Existing code reused and profile scope

`esp32/include/m4/hx711.h` reads actual signed HX711 counts; `calibration.h` and
`m4/arduino_io.h` load the existing explicit `m4-calibration/sensors-v2` factor.
No boot-time tare, no automatic inferred calibration and no second HX driver.
`m4/ledc_servo.h` is **the same GPIO6/50Hz LEDC adapter** used by the separate
`diag_servo_bench` profile; it is not a duplicate servo PWM driver.
`m4/dispense_bench.h` contains portable bounded state/guards, and
`src/dispense_bench.cpp` is its isolated supervised UART0 firmware.

`diag_dispense_bench` compiles only on the selected S3/16MB/noPSRAM/UART0
profile with explicit `DISPENSE_BENCH_MODE=1` and
`DISPENSE_BENCH_PHYSICAL_ENABLE=1`. **It CAN generate PWM GPIO6 after manual arm**;
normal `ACTUATOR_OUTPUTS_ENABLED=0` applies to other profiles/automatic paths.
GPIO4=DOUT,5=SCK,6=servo. GPIO7 pump is never configured/touched in this image.
Normal binary UARTv1/Jetson/CAT/DOG and the older servo-only/HX-only images remain
distinct; do not run the normal binary Jetson serial transport against this ASCII
firmware. No water or inventory pins assigned by this task.

## Sequence implemented — not a sensor-accuracy claim

DISARMED -> ARMED (candidate CLOSE PWM only) -> WAIT_BASELINE (four **new** fresh
validated HX readings with configured max range) -> OPEN bounded coarse/fine pulse
-> CLOSE candidate for350ms -> PWM OFF -> SETTLE at least configured time ->
MEASURE from four **new** fresh readings -> compute `stable_after-baseline` ->
COMPLETE if `dispensed >= target-tolerance`, otherwise another bounded pulse.
All decisions use measured stable feedback; no `servo time == grams` assumption.

- No scale calibration/freshreading/actual operator configuration -> reject before
  movement. A stored factor in NVS is not proof of *physical* calibration: the
  operator must provide prior HX711 real logs. Similarly configured microseconds
  are not proof the actual gate is closed; servo #2 physical validation precedes food.
- Configured `target`, `tolerance`, stable-range, fine-threshold, coarse/fine pulse
  durations, settle time and max measured grams are NOT final values. Portable
  absolute ceiling: target<=50g, measureddelta<=75g, maxpulses<=12, coarse<=250ms,
  fine>=20ms and<=coarse, settle500..5000ms, tolerance0..2g, stable-range>0..5g,
  total elapsed<=60s,4fresh samples/window and waiting timeout10s. These are
  **hard safety envelopes**, not tuned acceptance thresholds.
- NVS `dispense-bench/state-v1` write-ahead PENDING **before any OPEN**;
  unique strictly increasing ID1..16777215 prevents repeated bench requests
  across reboot. On abort/fault/reset with PENDING, boot refuses arming until
  explicit `dispense inspect YES` after operator checks the bowl/mechanics.
  Invalid/corrupt journal remains locked. No production daily/session quota or
  RTC schedule ownership implemented; maximum3 manual arms per boot only.
- Abort, deadline, HX fault, missing/stale/faulty reading, unstable baseline or
  post-pulse window, no progress, max pulses/grams, NVS fault, ADC invalid value
  and unexpected stable weight **decrease** fail closed and latch inspection.
  Every software fault commands candidate CLOSE if PWM still works, then stops
  PWM after the hold. Brownout, PWM write/detach failure or stalled mechanics
  cannot certify a physically closed gate; `servo_close_physical=UNVERIFIED`.
- A cat touching/eating from the bowl during dispensing can make net weight gain
  less than actual discharged food. The firmware rejects detectable drops, but
  cannot disambiguate simultaneous food removal from a still-positive net gain.
  Keep the cat away during every supervised bench dispense; stop if bowl/chute is
  touched or food spills outside the measured bowl. **Do not blindly top up.**
- The bench's stored `calibration_id` and monotonic sample time are checked within
  the session. Conversion drift, NVS hardware atomicity, mechanics/sensor noise,
  hard power-loss closure and tolerance remain subject to physical tests.

## Preconditions before ANY physical dispense

1. HX711 physical test #1 passed with raw zero stability, knownmass calibration,
   repeat knownmass validation **after actual reboot** on this bowl/loadcell mount.
2. Servo #2 bench logs prove GPIO6, safely calibrated candidate CLOSE/OPEN,
   no stall/hardstop/jitter/brownout, and a gate/return mechanism that actually
   closes after PWM is removed. If either test is absent, **do not flash-and-arm
   this combined image**; it cannot infer physical readiness from software tests.
3. Foodbowl is supported only by loadcell; chute/rim/cable don't bypassscale.
   Servo external5V with reviewed common logic reference; pump external branch OFF;
   hopper/servo enclosure clear of pets, hands, spills and unobserved loads.
4. Deliberate smalltarget, bounded pulse/threshold/stability values based on
   actual HX/servo evidence. **Do not start the first integration run at40g.**
   If a single pulse can exceed the chosen smallmax measuredgrams, don't arm.
   Mark physical tolerances/configuration as provisional until multiple trials.

## Build & SAFE application-only packaging (Windows PowerShell)

Working repo is the audited Gitmirror, not the old non-Git `D:\for_cat` snapshot:
```powershell
$Repo = 'C:\Users\chito\AppData\Local\Temp\opencode\for_cat_main_audit_full'
$Pio = 'D:\for_cat\.tools-venv\Scripts\pio.exe'
$Py = 'D:\for_cat\.venv\Scripts\python.exe'
$HXBundle = 'D:\for_cat\HX711_PHYSICAL_BRINGUP_20261021_PREP\deploy_hx711'
$Bundle = 'D:\for_cat\CLOSED_LOOP_DISPENSE_20261022_PREP_V2'
& $Pio run --project-dir "$Repo\esp32" -e diag_dispense_bench
& $Pio device list
# Existing $Bundle is a frozen exclusive output: only for a NEW version choose
# another output path before running prepare_dispense_bench.py again.
# & $Py "$Repo\scripts\prepare_dispense_bench.py" --pio $Pio --hx-bundle $HXBundle --output 'D:\for_cat\CLOSED_LOOP_DISPENSE_NEW_VERSION'
```
Package contains **firmware.bin ONLY**, not factory image. It verifies that
its compiled bootloader/partitions hashes match the HX-only image, but that is
NOT evidence of what is on your actual board. Preserve the physical HX calibration
in NVS: **NEVER flash a newly assembled factory image AFTER calibrating**.
The earlier `D:\for_cat\CLOSED_LOOP_DISPENSE_20261022_PREP` is a preserved
superseded preparation. The current V2 app is396352bytes with SHA256
`25775b3eb0f4d8434d9c6433e8aa8d7a59a24885d92d8abba3e7b1451f2439e7`.
Use only the V2 manifest/firmware for this runbook.

## Flash — only if actual installed bootloader/partitions match

Confirm serialport, actual ESP32-S3 and16MB flash, preserve real calibration data.
Use the current bundle manifest's image hash, not a previous version's. Use the
earlier HX bundle (from actual HX test) to verify **on-device** bootloader0x0 and
partitions0x8000. If the verify fails, STOP: app-only update is not justified.
This step must not overwrite NVS or recover with erase-all/stub.
```powershell
$Port = Read-Host 'Observed ESP32-S3 COM port'
$FlashPy = "$env:USERPROFILE\.platformio\penv\Scripts\python.exe"
$EspTool = "$env:USERPROFILE\.platformio\packages\tool-esptoolpy\esptool.py"
$Image = "$Bundle\firmware.bin"
$ExpectedHash = (Get-Content -Raw "$Bundle\deploy_manifest.json" | ConvertFrom-Json).firmware.sha256
if (-not $ExpectedHash -or (Get-FileHash -LiteralPath $Image -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedHash) { throw 'Image hash mismatch' }
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub flash-id
if ($LASTEXITCODE -ne 0) { throw 'ROM preflight failed: STOP' }
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub verify-flash 0x0 "$HXBundle\bootloader.bin" 0x8000 "$HXBundle\partitions.bin"
if ($LASTEXITCODE -ne 0) { throw 'Installed bootloader/partition mismatch: STOP' }
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub write-flash 0x10000 $Image
if ($LASTEXITCODE -ne 0) { throw 'App-only flash failed: STOP' }
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub verify-flash 0x10000 $Image
if ($LASTEXITCODE -ne 0) { throw 'App verify failed: STOP' }
```

**No port was enumerated or opened by this task; none of these physical commands
was run.** Matching bootloader/partition verify does not itself validate the
seller PCB/wiring, voltage, calibration or actuator mechanical closure.

## Interactive serial monitor (exclusive UART0)

```powershell
Push-Location $Bundle
try {
    & $Pio device monitor --port $Port --baud 115200 --eol LF --echo --dtr 0 --rts 0 --filter send_on_enter --filter log2file
} finally {
    Pop-Location
}
```
The RX output logfile appears under `$Bundle\logs`. This monitor does not
guarantee TX command recording; note the exact manual commands/ID/config in the
physical worksheet as well. Wait for every response. Close other UART readers;
`dispense` console is ASCII, not the normal Jetson binary protocol.

## First supervised physical progression / exact command syntax

**STOP if `CALIBRATION_LOAD code` is not2, if HX never becomes HEALTHY with fresh
grams, if servo CLOSE/OPEN physical settings were never validated, or if there
is no safe way to stop servo5V.** Code2 by itself is not physical calibrationPASS.

```text
dispense status
dispense test SMALL_TARGET_GRAMS 1
dispense inspect YES
dispense configure MIN_US MAX_US CLOSE_US OPEN_US COARSE_MS FINE_MS SETTLE_MS MAX_PULSES FINE_THRESHOLD_G TOLERANCE_G STABLE_RANGE_G MAX_TARGET_G MAX_MEASURED_G CONFIRM
dispense status
dispense arm YES
dispense test SMALL_TARGET_GRAMS 1
dispense status
dispense disarm
```

Fill all placeholders from **real prior physical measurements**; do not paste
placeholder text. RequestID is mandatory for cross-reset duplicate protection.
Only requestID1 for the first isolated test. `dispense inspect YES` is the
operator's claim that the bowl/servo/journal is physically inspected; it is not
an automatic validation certificate. If NVS journal is corrupted/invalid, this
command remains blocked: do not clear it with an erase-all shortcut.

Select an initial target that your own pulse/cell evidence shows is **smaller
than the full ~40g feeding goal** and within configured max. Suggested *sequence*
is tiny unloaded mechanical run (done in separate servo task) -> small food
trial with conservative pulse cap -> inspect weighed result -> new inspected trial
with next unique ID -> only then consider a larger target;40g only after repeated
real results. No universal safe smallgram amount/pulse duration/tolerance can be
deduced without your mechanism and scale readings. If maxpulses/no-progress/unstable
faults, inspect the rig; do not remove a guard simply to reach a number.

If error, stop with `dispense abort` and wait for `FAULT`/PWMoff. An aborted or
interrupted session leaves journal PENDING until `dispense inspect YES` after
physical inspection. Reboot does NOT resume an uncertain dispense. Do not
replay requestID1; choose a higher ID after inspection. Before additional test,
remember positions/config are RAM-only and need explicit reconfiguration after
inspect/reboot; <=3 arms/boot, no daily feeding authority. No animal by the bowl.

## Expected firmware observability (numbers only from actual sensors)

- Boot prints `DISPENSE BENCH ONLY DISARMED ... CALIBRATION_LOAD code=... JOURNAL code=...`.
- `dispense status` prints state/health/raw/grams/config/request/pulse/PWM and
  `pump=OFF cat_auto=OFF web=OFF physical_validated=false`.
- Disarmed `dispense test <target> <id>` -> `NOT_ARMED`, no GPIO6 PWM movement.
- `dispense inspect YES` -> `ACCEPTED` only after operator action/NVS readback.
- Config -> `ACCEPTED` only when all windows/bounds finite and within ceilings;
  status echoes microseconds/settle/coarse/fine/stability/tolerance/limits.
- ARM -> `ACCEPTED` only if calibrated/fresh HX711; may move immediately to
  previously physically verified CLOSE candidate.
- TEST -> `event=START` target; then `event=BASELINE` after four stable NEW samples;
  each `event=COARSE|FINE` includes pulse_ms/count; `event=CLOSE_COMMANDED`,
  `event=SETTLING`, then `event=MEASUREMENT` stableafter/delta/remaining.
- `event=COMPLETE` requires measured target-minus-configured-tolerance and
  durable journal clear; `servo_pwm_attached=0`. `servo=CLOSE...UNVERIFIED` is not
  a physical gate contact sensor. An overshoot is logged, never hidden.
- Faults print a distinct reason, stop further pulses and require inspection;
  fault while PWM active commands CLOSE candidate if possible, holds boundedly,
  then PWMoff. If PWM/hardware fails, actual mechanical closure CANNOT be assured.

`host_checks/.../closed_loop.serial.log` is a **FAKE HX711/LEDC/NVS illustration**,
not actual dispense evidence or recommended physical pulse settings.

## PASS / FAIL / what to send

Software HOST/COMPILE PASS is separate. **Physical PASS needs operator evidence:**
stable HX baseline and afterpulse windows; food visibly falls into the weighed
bowl; every pulse returns to mechanically CLOSED; positive measured stable delta;
stops on loadcell feedback (not just fixed time), correct coarse/fine transition,
bounded pulse/time/gram guards and abort/fault closure with power stable; multiple
real trials have agreed error/tolerance and no stall/reset. A separate physical
interlock/feedback may be necessary to demonstrate closure on powerloss.

FAIL or stop if HX calibration missing/unstable, bowl touches the frame, reset or
NVS fault, servo hardstop or gate cannot close, PWMoff does not hold gate closed,
food spills, cat approaches during test, maxpulse/time/grams fault, or error beyond
an acceptance tolerance chosen from actual data. NVS `PENDING` after an abort is
intentional fail-closed; it is not permission to repeat the same ID.

For each real trial record target, requestID, calibration reference/ID, initial
stable grams, all raw/stable postpulse grams, coarse/fine counts and times,
dispensed delta/overshoot, elapsedms, configured CLOSE/OPENus, HX noise/settle,
ESP32 resets/brownout, servo stall/heat, hopper/bowl losses, food falling outside
scale, and actual mechanical gate closure. Send serialRX log, typed commands,
independently weighed before/after food if possible, servo wiring/photos and video.
No values above are fabricated as real readings. **Until received: PHYSICAL NOT
VERIFIED; ~40g accuracy NOT ESTABLISHED.**
