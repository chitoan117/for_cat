# GPIO6 SERVO bench — record only physical observations

Status before evidence: **PHYSICAL NOT VERIFIED**. Copy this template to a new
file before entering readings; leave original release artifact untouched.

## Identity/wiring
- Board exact model, observed COM, chip/16MB ROM preflight output:
- Flashed factory SHA256, flash verify output:
- Servo actual model, documented pulse interval:
- Servo GPIO6 wiring photo:
- External5V supply type/rated current and measured voltage:
- Confirm shared signal-reference GND and pump/F5305S unpowered:
- Hopper empty, horn disconnected/gate unloaded/no cat:
- Servo gate mechanical return mechanism if any:
- Complete serial RX logfile path including boot and disarmed rejection:
- Continuous video/photographs of motion and power wiring:

## Serial sequence / observations
- Cold boot `servo status` output (`state=DISARMED`, PWM off?):
- `servo open`/`servo set` while disarmed: exact rejection and actual stillness:
- Actual typed `servo configure MIN MAX CLOSE OPEN CONFIRM` (microseconds):
- Reason each candidate is within actual servo manufacturer's pulse range:
- Motion at configuration before arm? (expected NO):
- `servo arm YES`: log and movement toward candidate CLOSE:
- `servo open`/`servo set` once per arm: exact log + observed direction:
- Automatic return-to-CLOSE log; time to PWM-off/disarm:
- Manual `servo close` when armed and `servo disarm` observations:
- Motion command after disarm: exact rejection and stillness:
- Number of arms/moves this boot (maximum 3 arms):
- Unexpected UART noise/errors/`OUTPUT_FAULT`/`PWM_OFF_FAILED`/hard deadline:
- Behavior on actual EN/RST after the first safe horn-detached motion; output
  must start DISARMED, not auto re-arm (mechanical closure still not assumed):

## Physical measurements
- Candidate CLOSE in us / gate actually closed? (not attached => NOT VERIFIED):
- Candidate OPEN in us / gate opens enough? (not attached => NOT VERIFIED):
- Correct direction? YES / NO / UNKNOWN:
- Servo jitter? YES / NO, details:
- ESP32 reset/brownout? YES / NO, include reset logs:
- Mechanical stall/hardstop? YES / NO, details:
- Unexpected repeated movement? YES / NO:
- Excessive heat/supply drop/cable movement? YES / NO, measurements:
- Gate state if servo power lost while OPEN (do not create an unsafe release):
- Real close/open position confirmed without hard stop? YES / NO:

Outcome remains **PHYSICAL NOT VERIFIED** until operator evidence reviewed. HX711
physical status separately remains unverified until its own calibration logs.
