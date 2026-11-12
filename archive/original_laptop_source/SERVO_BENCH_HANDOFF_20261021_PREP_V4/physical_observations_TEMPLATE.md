# Servo GPIO6 physical observations — fill from the actual supervised test

**Current classification: PHYSICAL NOT VERIFIED.** Copy this template before
recording; do not edit the published release. Host checks cannot fill this in.

## Hardware and evidence
- Board model, COM, chip/flash ROM preflight output:
- Firmware factory SHA actually flashed, `verify-flash` result:
- Servo manufacturer/model and actual documented pulse interval:
- GPIO6 signal wiring photo:
- External5V source rating, common GND, measured idle/moving voltage:
- Pump/F5305S unpowered, hopper empty, horn disconnected, no cat:
- Serial RX logfile including boot/command results/timeouts/reset:
- Video of stillness before arm, small motion, return, disarm:
- Gate return spring/independent closure feedback if installed:

## Serial console observations
- Initial `servo status` DISARMED/output_pulse_us=0?:
- `servo open` and `servo set` while disarmed: exact REJECTED outputs, stillness:
- Typed `servo configure MIN MAX CLOSE OPEN CONFIRM` (microseconds):
- Why candidate values fit *this* servo model; horn detached:
- Any movement caused by configure alone? (expected NO):
- `servo arm YES`: exact log; candidate CLOSE caused motion?
- `servo open` or one bounded set: exact log + observed direction:
- Auto `MOVE_TIMEOUT_RETURN_TO_CLOSE_REFERENCE` and
  `PWM_OFF_DISARMED_CLOSE_UNVERIFIED`: time/motion:
- Manual `servo close` from ARMED (<2s), disarm after close:
- After disarm: command rejection and stillness:
- Actual reset during unloaded test: boot returns DISARMED/configured0, no rearm:
- Any OUTPUT_FAULT / PWM_OFF_FAILED / HARD_DEADLINE / UART fault:

## Mechanical/power observations
- CLOSE candidate pulse in us; gate PHYSICALLY closed? (if horn detached: unverified):
- OPEN candidate pulse in us; enough clearance for food? (if detached: unverified):
- Direction correct? YES / NO / UNKNOWN:
- Jitter observed? YES / NO, details:
- ESP32 resets/brownouts? YES / NO; full boot logs:
- Mechanical stall/hard-stop? YES / NO; details:
- Unexpected repeated movement? YES / NO:
- Heating / current / measured5V dip if available:
- Powerloss/open-gate physical return (only if safe to test):
- Actual mechanical close feedback? YES / NO:

Servo PHYSICAL PASS is pending real motion, closed/open mechanism and fault
behavior evidence; PWM-off is not proof of closure. HX711 physical PASS is a
separate task requiring its own real logs.
