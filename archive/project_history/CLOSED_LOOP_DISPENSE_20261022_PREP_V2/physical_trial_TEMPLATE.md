# Physical supervised closed-loop dispensing — actual trial evidence ONLY

**PHYSICAL NOT VERIFIED** until operator logs/video are inspected. Copy this
template to a NEW observations file; do not replace the published template.

## Prerequisites
- Real HX711 #1 tare/reference/zero-stability/persistence validation log path:
- Real servo #2 CLOSE/OPEN physical microseconds/mechanics test log and video:
- Foodbowl supported only on loadcell, no chute/rim/cable bypass:
- GPIO4DOUT/5SCK/6signal, servoexternal5V/commonGND, pumpunpowered photo:
- Board model/observed COM/ROM16MB result:
- On-board bootloader/partitions verify-flash outputs vs HX profile:
- App-only flash firmwareSHA256 and verify result:
- No cat/human/bowl disturbance, external5V PSU and means to cut power:

## Exact manual bench settings
- Status `CALIBRATION_LOAD code=2`, hx_health, calibration_id and current grams:
- Operator actually inspected bowl/gate and typed `dispense inspect YES`:
- Full `dispense configure MIN MAX CLOSE OPEN COARSE FINE SETTLE MAX_PULSES FINE_THRESHOLD TOLERANCE STABLE_RANGE MAX_TARGET MAX_MEASURED CONFIRM` line:
- Evidence for pulse durations, stability range, target tolerance (physical, NOT host fixture):
- Status showing accepted configuration and `inspection_required=0`:
- Typed `dispense arm YES` and `dispense test TARGET_G UNIQUE_ID`:

## Real results for EVERY trial (first target SMALL, not automatically40g)
- Trial ID, actual target_grams, starttime:
- Four NEW stable baseline grams/samples and timestamps:

| Pulse | COARSE/FINE | open_ms | Close event observed | Four stable after_g samples | Delta from baseline_g | Remaining_g |
|---|---|---:|---|---|---:|---:|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

- Total pulses/coarse/fine, elapsed_ms:
- Afterstable / actual dispensed_grams:
- Independent manually weighed food before/after if available:
- Overshoot_grams = max(0, afterminusbaseline-target) or UNKNOWN if invalid:
- Actual gate mechanically CLOSED after each pulse/completion/abort/fault?:
- HX readiness/faults/noise/range and NVS journal state:
- ESP32 resets/brownouts? yes/no/logs:
- Servo stall/jitter/hardstop/heat? yes/no:
- Food outside bowl/animal touched or ate during feed? yes/no/attribution:
- Complete raw serialRXlog path, exact TXcommands, videos/photos:

## Repeatability / conclusion
- Multiple different trial targets including later~40g (only after smaller tests):
- Actual errors and acceptance tolerance chosen from measurements:
- Tested max pulse/time/gram and abort/fault behavior physically? Logs:
- Does a physical return/interlock ensure closure even during MCU/power loss?:
- Servo/HX separate physical PASS already supported? (attach sources):
- Final result: **PHYSICAL NOT VERIFIED until actual rig evidence reviewed**
