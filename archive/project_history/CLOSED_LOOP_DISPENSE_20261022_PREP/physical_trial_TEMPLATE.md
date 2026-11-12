# Physical closed-loop food trial — complete from ACTUAL rig only

Current status **PHYSICAL NOT VERIFIED**. Copy before filling. No numbers are
pre-accepted; any software fakegrams from host_checks are NOT food measurements.

## Prerequisite real evidence
- HX711 tare, known reference, post-reboot validation raw log/path/date:
- Food bowl mounted entirely on scale without rim/chute/cable contact:
- Servo-only bench real CLOSE/OPEN microseconds and mechanical-gate video/path:
- Power wiring external5V servo, common GND; pump unpowered:
- Food path/bowl weighed; cat excluded and no manual interference:
- Firmware app SHA256 and verified installed bootloader/partition hashes:
- Observed COM/board/16MB ROM preflight and app-only flash verify output:

## Exact operator configuration (no invented defaults)
- `dispense inspect YES` time and physical inspection performed:
- `dispense configure MIN MAX CLOSE OPEN COARSE FINE SETTLE MAX_PULSES FINE_THRESHOLD TOLERANCE STABLE_RANGE MAX_TARGET MAX_MEASURED CONFIRM` (type ACTUAL values):
- Basis for coarse_ms/fine_ms/settle_ms/stability_range/tolerance choices:
- Firmware `DISPENSE_STATUS` with calibration/health/config/PWM:

## Each trial, begin SMALL before any ~40g trial
- Unique request_id (strictly increasing1..16777215):
- Target_grams:
- Baseline stable grams/four NEW samples:
- Calibration fingerprint and actual reference mass:

| Pulse | Mode COARSE/FINE | Configured open_ms | Stable after_g | Delta from baseline_g | Remaining_g | Closed mechanically? |
|---|---|---:|---:|---:|---:|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

- Total coarse_pulses / fine_pulses / total pulses:
- Actual dispensed_grams from scale after settling:
- Independent before/after food mass if measured:
- Overshoot_grams = max(0, actual_dispensed-target), or unknown if invalid:
- Elapsed_ms, minimum actual settle time:
- Final servo state physically CLOSED? (not merely PWMoff/commanded):
- `DISPENSE COMPLETE` / `FAULT` with exact reason and NVS journal state:
- HX711 zero drift / sample health / unstable periods / fault:
- ESP32 reset/brownout? yes/no + boot output:
- Servo stall/hard-stop/heating? yes/no + details:
- Food spilled/animal touched/moving bowl? yes/no + attribution uncertainty:
- Abort/fault/limit test if safely conducted, did gate physically close?:
- Full serial RX logfile and order of commands typed:
- Video/photos of foodfall/servo gate/scale and supply readings:

## Physical reviewer decision
- Trial is supervised only, no CAT/Web/scheduler actuation:
- Multiple real trials with tolerated error and repeatability available?:
- Specific accuracy target and actual errors (not assumed):
- Servo physical CLOSE guaranteed on powerloss/fault? Evidence:
- HX711 actual calibration still valid?:
- Final status: **PHYSICAL NOT VERIFIED until actual logs are reviewed**
