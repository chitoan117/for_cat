# SERVO physical bring-up #2 — guarded GPIO6 bench, NOT PHYSICALLY VERIFIED

**2026-10-21 scope:** supervised food-gate servo only. Existing
`m4::ServoInterface`/`DisabledServo`, `InertServo` and normal safety policies
were audited and preserved. None implements PWM; the isolated
`m4/servo_bench.h` policy + `src/servo_bench.cpp` contain the first actual PWM
adapter, exclusively for this profile. Normal binary firmware and all other
diagnostic profiles remain inert.
CAT/DOG source/engine/binary, pump, Web, HX711 and feed protocol are unchanged.
Earlier “no servo tester exists” statements in this document are obsolete.
HX711 has a prepared diagnostic workflow but **no PHYSICAL PASS from actual logs**.

## Actual safety boundary / limits

Profile **`diag_servo_bench`** is deliberately selectable, not default (`esp32dev_sim`
remains PIO default). It compiles only for ESP32-S3/16MB/noPSRAM/UART0 HW_SAFE with
explicit `SERVO_BENCH_MODE=1` and `SERVO_BENCH_PHYSICAL_ENABLE=1`. Normal
`ACTUATOR_OUTPUTS_ENABLED=0` remains unchanged: **this bench image is the one
explicit, separate exception that CAN output PWM on GPIO6 after a manual arm**.
That flag is not a claim of zero bench PWM. GPIO7 pump is never configured.

At boot GPIO6 is held LOW, PWM **not attached**; state DISARMED, no stored position.
Every reset loses the in-RAM positions and arm state. No feed/AI/API/scheduler or
automatic servo call exists in this image. Only serial commands can move it.

An operator must first enter provisional microsecond values:
`servo configure SAFE_MIN_US SAFE_MAX_US CLOSE_CANDIDATE_US OPEN_CANDIDATE_US CONFIRM`.
The configured window must be within the **initial electrical test envelope**
1000..2000us, width<=100us, distinct close/open inside that window; configuration
can occur once per boot, only while DISARMED. These caps constrain software, **not
guarantee the attached servo/mechanism is safe**. Confirm the actual servo model's
pulse range before use. No physical gate angles/positions were invented or saved.

- `servo arm YES` attaches Arduino3.3.11 LEDC pin API to **GPIO6 only**,50Hz,
  16-bit duty, at the supplied candidate CLOSE. This may move the horn! Perform
  the first test with horn detached and no food; it is NOT proof of a closed gate.
- One `servo open` or `servo set PULSE_US` per arm; set stays inside configured
  range, no arbitrary angle/raw PWM. OPEN held<=250ms, then candidate CLOSE for
  350ms; PWM detached and GPIO6 LOW, auto-DISARMED.
- Armed without movement returns to reference after<=2000ms. Any still-active
  operation reaches hard deadline<=3000ms, PWM OFF and FAULT; **actual mechanical
  closure is not guaranteed at hard deadline or LEDC failure**. Error logged.
- `servo close`/`servo disarm` trigger candidate CLOSE+bounded hold, then LOW/off.
  Other motion commands during CLOSING are rejected. Maximum **3 arms per boot**;
  no automatic re-arm or NVS state. Reboot starts DISARMED again and must NOT be
  used as a way to automate repeated bench movement.
- Every command/action, reject, timeout, close/off/fault logs a monotonic sequence.
  This is a loop-driven timeout: blocked MCU, brownout or stuck servo cannot be
  certified safe by host fakePWM tests. Physical spring/normally-closed fallback
  or independent interlock and real closure feedback are future safety gates.
  LEDC PWM stop/detach failure is reported `PWM_OFF_FAILED_FAULT_REMOVE_SERVO_POWER`;
  the controller remains FAULT and refuses rearm. Cut external servo5V in that case:
  a returned software status is not proof the PWM wire or gate reached CLOSE.

This image does NOT implement production close/open calibration, grams dispensing,
CAT/near feeding or other actuator use. Do not attach food or leave servo powered
unattended while running it.

## Electrical / mechanical preflight

1. Record exact servo model/datasheet-supported pulse interval. With power OFF,
   confirm GPIO6 signal to intended servo, separate suitable **external5V** V+,
   verified common signal reference GND. Do **not** use ESP32 3V3 or Jetson header
   to power a moving servo; leave pump/F5305S branch disconnected.
2. Inspect supply current capability/brownout protection, exposed wires and a
   fast way to remove servo power. Position the servo/horn so a small test cannot
   trap fingers; **horn disconnected from food gate**, hopper empty, no animal.
3. Identify a provisional CLOSE-reference pulse and small direction of movement
   from the actual servo documentation/setup. Without that, stop at `servo status`
   and disarmed rejection; do NOT arm. Not even a common 1500us is automatically
   the true closed angle for an unknown linkage.

## Build and prepare — Windows PowerShell

The working tree is the audited Windows Gitmirror, not the older non-Git snapshot
at `D:\for_cat`. A separate versioned bundle is available at
`D:\for_cat\SERVO_BENCH_HANDOFF_20261021_PREP_V4`; use its OWN manifest/hashes, not
the earlier PREP/PREP_V2/PREP_V3, sensor-only or V2 factory images. Prior bench
bundles remain preserved as superseded preparation evidence. V4 includes host
reset-mid-motion verification and the final firmware resource figure.
Creating another bundle requires a NEW path.

```powershell
$Repo = 'C:\Users\chito\AppData\Local\Temp\opencode\for_cat_main_audit_full'
$Pio = 'D:\for_cat\.tools-venv\Scripts\pio.exe'
$Py = 'D:\for_cat\.venv\Scripts\python.exe'
$Bundle = 'D:\for_cat\SERVO_BENCH_HANDOFF_20261021_PREP_V4'
& $Pio run --project-dir "$Repo\esp32" -e diag_servo_bench
& $Pio device list
# Only if packaging a new revision into a NEW folder:
# & $Py "$Repo\scripts\prepare_servo_bench.py" --pio $Pio --output 'D:\for_cat\SERVO_BENCH_HANDOFF_ANOTHER_VERSION'
```

The bundle manifest is explicit: **PWM possible after manual configuration/arm**;
factory image overwrites covered NVS/gaps. No automatic board flash occurred.
Current V2 app SHA256:
`53f046e26aa44ce326338048b54122cbf7f83efffe0dd99bed0ebd2dd710a3ab`;
factory SHA256:
`b96862a9ee1681536a033b52dc2863ead421b73a48d2de546f37390606001a83`.
Build result RAM23816B, linkedflash373109B; firmware.bin378016B,
factory443552B. These are build/artifact measurements, not mechanical evidence.

## Flash manually, only after reviewing covered NVS/board identity

Close other monitors; use the actual `pio device list` COM, not a guessed number.
Do the ROM preflight with servo external5V initially **disconnected**.
```powershell
$Port = Read-Host 'Observed ESP32-S3 COM port'
$FlashPy = "$env:USERPROFILE\.platformio\penv\Scripts\python.exe"
$EspTool = "$env:USERPROFILE\.platformio\packages\tool-esptoolpy\esptool.py"
$Image = "$Bundle\firmware.factory.bin"
$ExpectedHash = (Get-Content -Raw "$Bundle\deploy_manifest.json" | ConvertFrom-Json).files |
    Where-Object { $_.file -eq 'firmware.factory.bin' } |
    ForEach-Object { $_.sha256 }
if (-not $ExpectedHash -or (Get-FileHash -LiteralPath $Image -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedHash) { throw 'Factory SHA mismatch' }
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub flash-id
if ($LASTEXITCODE -ne 0) { throw 'ROM preflight failed; stop' }
```

Confirm ROM reports **ESP32-S3 /16MB**, backup/review covered NVS/partition data.
Only then, in a supervised session with actuator still unpowered:
```powershell
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub write-flash 0x0 $Image
if ($LASTEXITCODE -ne 0) { throw 'Flash failed; stop' }
& $FlashPy $EspTool --chip esp32s3 --port $Port --baud 115200 --no-stub verify-flash 0x0 $Image
if ($LASTEXITCODE -ne 0) { throw 'Verify failed; stop' }
```

Do not use `diag_hx711`, oldV2 sensor images or normal binaryUART firmware for
this servo bench. A subsequent actual reboot/resets arm state; it does not prove
the gate physically closed when servo power was removed.

## Interactive monitor + complete transcript

After checking wiring/servo model, power the servo from its separate5V branch.
Open one monitor; note the actual log filename. Logging filter records received
device output, not guaranteed typed commands: record command order separately.
```powershell
Push-Location $Bundle
try {
    & $Pio device monitor --port $Port --baud 115200 --eol LF --echo --dtr 0 --rts 0 --filter send_on_enter --filter log2file
} finally {
    Pop-Location
}
```
This mode's console says `SERVO BENCH ONLY GPIO6 PWM_OFF DISARMED`. A syntax
mistake or overly long input is rejected/discarded, never used as raw PWM.

## First physical test: horn disconnected, hopper empty, pump unpowered

Wait for each command/result. Do not paste a batch of lines.

| Order | Type | Expected response / behavior |
|---:|---|---|
| 1 | `servo status` | `state=DISARMED configured=0 output_pulse_us=0`, no PWM/motion |
| 2 | `servo open` | `REJECTED_NOT_ARMED`, no movement |
| 3 | `servo set 1500` | `REJECTED_NOT_ARMED`, no movement; numeric value is only a parser example |
| 4 | `servo configure MIN MAX CLOSE OPEN CONFIRM` | Only operator-chosen **microseconds** from actual servo model: `action=CONFIGURE result=ACCEPTED`; configuration alone produces no PWM |
| 5 | `servo status` | DISARMED, configured1, candidate values echoed; no PWM |
| 6 | `servo arm YES` | `action=ARM result=ACCEPTED state=ARMED pulse_us=CLOSE`, horn may move to candidate reference |
| 7 | `servo open` **or** `servo set PULSE_US` | `action=OPEN/SET result=ACCEPTED state=MOVING`, exactly one small move in configured range |
| 8 | wait and `servo status` | Auto log `MOVE_TIMEOUT_RETURN_TO_CLOSE_REFERENCE`, then `PWM_OFF_DISARMED_CLOSE_UNVERIFIED`, stateDISARMED |
| 9 | arm again, then `servo close` promptly (<2s) | Manual CLOSE enters CLOSING; wait for PWM_OFF_DISARMED; at most3 arms perboot. OPEN automatically closes within250ms, so do not rely on a human being fast enough to issue CLOSE during OPEN. |
| 10 | `servo disarm`, `servo open` | disarm accepted when already disarmed, subsequent move `REJECTED_NOT_ARMED` |

**Do not literally type MIN/MAX/CLOSE/OPEN**. Example **ONLY if servo datasheet
supports this interval and the horn is detached**: `servo configure 1450 1550 1500 1520 CONFIRM` (a <=100us test window). These are NOT verified physical close/open settings. If the linkage needs more than a100us span to open fully, record the limitation; don't widen firmware cap or force gate against a stop in this first test.

`servo set PULSE_US` must be inside configuredMIN..MAX and different from CLOSE.
Only one OPEN/SET command per arm; repeated commands are rejected. If the horn or
gate moves unexpectedly, jitters, stalls, heats, or ESP32 resets, cut servo5V,
stop testing and keep full logs. Poweroff during OPEN may leave a mechanically
open gate: current firmware cannot guarantee closure without physical return
mechanism/feedback. A software timeout/PWM_OFF is not a physical closure sensor.

## Physical gate calibration (separate supervised observation)

If initial horn-detached tests are safe, physically identify the candidate
direction, actual CLOSE and actual safe OPEN positions with mechanism unloaded.
Document microsecond widths and whether gate fully closes/opensenough without
hard stops or stall. Do not declare OPEN_POSITION valid based solely on `ACCEPTED`
or reuse sample pulse values. This initial envelope may require a separately
reviewed wider calibration mode if the mechanism cannot open in <=100us.

## PASS / FAIL / report back

**PHYSICAL PASS only after your real logs and video** show intended GPIO6 motion,
disarmed rejection/stillness, bounded move/automatic candidate CLOSE, real
mechanical CLOSE and sufficiently open gate, no unexpected repeats, no brownout/
stall, and disarm blocking movement. Record confirmed microseconds/direction,
5V supply behavior and horn/linkage mounting. If the gate hasn't reached real
close/open or the 100us test is insufficient: **PHYSICAL NOT VERIFIED** for
fullservo foodgate calibration, even when software tests pass.

FAIL includes disarmed motion, repeated/unbounded movement, stop/hardstop, no
valid CLOSE, inability to disarm, resets/brownout, supply collapse/heat, mismatched
GPIO, unexplained rearming or failed PWM OFF. `OUTPUT_FAULT`/`HARD_DEADLINE...`
mean PWM disabled/FAULT, **not proof of physically closed gate**.

Please send full RXserial log including boot, each command and event sequence;
photos of GPIO6/external5V/commonGND/horn/linkage; video of disarmed, small move,
return/disarm; servo model/datasheet; observed CLOSE/OPEN microseconds, direction,
jitter yes/no, MCU reset/brownout yes/no, stall/hardstop yes/no and heating/5V
droop observations. HX711 remains PHYSICAL NOT VERIFIED until its own evidence.

The *next* milestone, after both servo and HX711 physical gates, is bounded
pulse-close-settle closed-loop addedgrams≈40g. No actuation of that path exists
in this bench image.
