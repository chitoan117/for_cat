# GPIO6 SERVO supervised bench — operator evidence (fill ONLY real observations)

Current status: **PHYSICAL NOT VERIFIED**. Do not fill PASS from host logs.

## Identity / setup
- Actual ESP32-S3 board / ROM flash result / COM:
- Firmware exact factory SHA256 flashed:
- Actual servo manufacturer/model/datasheet pulse interval:
- Servo GPIO6 signal wiring photo:
- External5V source/current rating/observed voltage (idle/move):
- Common ESP32/servo signal-reference GND confirmed:
- Pump/F5305S branch unpowered (yes/no):
- Hopper empty, horn detached, food absent, animal absent (yes/no):
- Physical gate return mechanism/closed-position feedback if any:
- Serial RX log path (including boot/arm/reject/timeouts/reboot):
- Video/photo evidence path:

## Serial console observations
- Boot disarmed/PWM-off output:
- `servo status` state/configured/output pulse:
- `servo open` while disarmed exact REJECTED response and observed stillness:
- `servo set ...` while disarmed exact REJECTED response:
- Full `servo configure MIN MAX CLOSE OPEN CONFIRM` command (microseconds):
- Why these pulse values were selected from ACTUAL servo datasheet/mechanism:
- Any motion during configuration before arm?:
- `servo arm YES` output + horn motion at candidate CLOSE:
- Exact `servo open` or bounded `servo set` output + observed direction:
- Time to automatic `MOVE_TIMEOUT_RETURN_TO_CLOSE_REFERENCE`:
- Time to PWM-off/disarmed, any movement after disarm:
- Manual `servo close` outcome (if tested):
- Motion command after disarm exact rejection:
- Attempts/arms used (maximum 3 per boot):
- Any OUTPUT_FAULT / PWM_OFF_FAILED / HARD_DEADLINE / unexpected reset:

## Mechanical & electrical measurements
- Provisional close pulse_us / actually closed gate? (yes/no/not attached):
- Provisional open pulse_us / actually enough to release food? (yes/no/not attached):
- Direction correct? (yes/no/unknown):
- Jitter observed? (yes/no + details):
- Mechanical hard stop/stall? (yes/no + details):
- Unexpected repeated motion? (yes/no + details):
- ESP32 reset/brownout? (yes/no + logs):
- Servo temperature, 5V dip / estimated current if measured:
- Result when servo power removed while gate open (do not cause unplanned release):
- Has actual mechanical CLOSE after PWM fault/power loss been demonstrated?:

## Pending classification
- Host build/tests: see separate summary; NOT physical evidence.
- Servo GPIO6 motion: PHYSICAL NOT VERIFIED
- Disarmed rejection/stillness: PHYSICAL NOT VERIFIED
- Mechanical CLOSE/OPEN: PHYSICAL NOT VERIFIED
- Power and timeout: PHYSICAL NOT VERIFIED
- HX711/load cell: PHYSICAL NOT VERIFIED unless its separate real logs are reviewed
- Final outcome: **PHYSICAL NOT VERIFIED**
