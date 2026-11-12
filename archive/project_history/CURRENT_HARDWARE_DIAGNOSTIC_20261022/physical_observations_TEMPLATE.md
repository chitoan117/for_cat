# Current wired hardware — operator observations, in REQUIRED test order

**Before receiving actual evidence: WIRED (owner-reported), PHYSICAL NOT VERIFIED.**
Copy to a new file; do not overwrite this template. Two reservoir sensors are
**NOT WIRED**, not failed. Attach raw serialRX logs and command order/video/photos.

## Setup
- Board/module identification, serial COM/USB bridge, ROM16MB preflight:
- Current sensor firmware app SHA256 / app-only flash verify:
- Actual bootloader/partition verify status, NVS calibration preserved:
- Wiring/photo, HX/RTC/OLED3V3, sensor5V supply and Echo divider voltages:
- Servo and pump external5V branches DISCONNECTED during steps1–7:
- Serial logfile path(s), operator/time:

## 1. ESP32 boot stability
- Commands: `status` / reboot; boot text and reset reason:
- Reboot loop/watchdog/brownout? yes/no/log:
- Servo unexpected motion / pump unexpected flow? yes/no and power state:
- UART stable/readable? yes/no:

## 2. OLED
- `oled_health`, `oled_address=0x3c`, `oled_initialized`:
- Panel physically shows local data? photo/video:
- I2C supply/pull-up voltage if measured:

## 3. DS1302
- `rtc_detected`, `rtc_health`, actual `rtc_utc`:
- Actual known UTC reference and difference:
- Only if needed, explicit `set-utc ACTUAL_UTC CONFIRM`, readback:
- Battery/retention after powercycle:

## 4. PIR
- Still state / `pir_transition_count` / last timestamp:
- Motion state after moving / time to transition:
- Leaving field / time to reset LOW after module delay:
- No inference that PIR identifies CAT:

## 5. HX711 food-bowl scale
- Bowl mounting fully supported by loadcell, no contact with enclosure:
- Initial raw_counts / health / calibration / grams / sample age:
- Five `avg 16` raw means with no additional tare during repeats:
- Tare and actual known reference mass if needed, no guessed mass:
- `validate ACTUAL_REFERENCE_GRAMS 16` measured/reference/error:
- Selected REAL range for `weight-stability REAL_MAX_RANGE_G CONFIRM`:
- Four NEW window size/range and `weight_stable` status:
- Save/reboot validation logs if newly calibrated:

## 6. HC-SR04 #1 (approach ONLY)
- Verified voltage at GPIO13 **after divider** (not 5V):
- `echo-approach-3v3 CONFIRM` result:
- True measured near/mid/far cm and reported raw/filtered cm/validity:
- Timeout count before/after test, stuck/invalid result:
- No servo/feed command from distance:

## 7. JSN-SR04T #1 (operational water ONLY)
- Verified voltage at GPIO15 after divider:
- `echo-water-3v3 CONFIRM` result:
- Actual LOW / NORMAL / TARGET water conditions with real geometry:
- Actual measured water distance/validity/timeout count:
- Blind-zone/placement fit? yes/no; water% null until real FULL/EMPTY calibration:
- Pump actually remained disconnected/OFF, no autonomous refill:

## 8. SERVO (separate supervised image)
- Restore no pump power. Actual servo model/datasheet/external5V/commonGND:
- `diag_servo_bench` exact image SHA flashed and verified:
- Initial `servo status` DISARMED and motion while disarmed? (expected none):
- CLOSE/OPEN candidate µs and actual gate positions/direction:
- Manual arm, small OPEN, automatic CLOSE/disarm logs/video:
- ESP32 brownout/jitter/stall/hardstop/5V dip:
- Gate CLOSE physically confirmed, not only PWM OFF?:

## 9. PUMP / F5305S (separate pump-only image)
- Servo power disconnected, pump outlet/containment prepared:
- `diag_pump_bench` inert no GPIO7/pump OFF? operator observation:
- Exact F5305S module label/schematic, IN active polarity measured:
- OFF input bias during ESP32 boot/reset measured:
- Only after polarity proof, chosen active_high or active_low app SHA:
- `pump status`, disarmed ON rejection, manual `pump arm YES`:
- `pump on ACTUAL_BOUNDED_MS` duration and motor/flow confirmation:
- Automatic OFF, manual `pump off`, `pump disarm`, motion blocked after disarm:
- Supply voltage/current, sensor behavior before/after, UART resets/brownouts:
- No autonomous water control, DRINKING/AI not used:

## Unwired inventory
- HC-SR04 #2: **NOT WIRED**, TRIG/ECHO TBD; no percent/readings expected.
- JSN-SR04T #2: **NOT WIRED**, TRIG/ECHO TBD; no percent/readings expected.

## Outcome
- User-reported physically WIRED components that passed real evidence:
- Components still PHYSICAL NOT VERIFIED (include actual reason):
- Active F5305S OFF polarity/bias proven? YES/NO:
- Any observed faults and exact full logs/photos:
- Final physical classification: **NOT YET REVIEWED**
