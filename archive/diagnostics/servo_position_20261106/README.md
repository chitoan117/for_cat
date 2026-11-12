# Servo fixed-position feasibility review

Owner requests fixed OPEN and CLOSED positions, no fine adjustment, servo-only scope.

Current source: D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino
SHA256: F5D24AE815D34DCCD2BA3EA2482FFE12786C63F23A64EEF70912B8138FCEC45C

Owner hardware reference is a continuous-rotation MG996R360. Current output is speed/direction control:1400us opening,1600us closing,1500us neutral;1100ms/900ms timed travel. No measured angle or two endpoint sensors. GPIO47 remains explicitly disabled by owner. Current source has no fine-adjust command or170ms constant.

Observed code: manualServoMove rejects requests while busy but accepts the same direction again after DIAG_OPEN/DIAG_CLOSE returns to IDLE. Thus repeated completed OPEN commands can continue rotating farther. A software duplicate-command guard could prevent those repeated strokes, but cannot prevent drift across legitimate OPEN/CLOSE cycles, neutral creep, or motion after interruption/reset, nor measure endpoints.

A true fixed-position solution requires positional feedback (appropriate angular servo or encoder/end-position sensors). Do not replace speed pulses with supposed angles on this continuous servo, guess new equal timings, add stall-against-stop homing, or claim fixed endpoints from elapsed time. Await owner hardware choice before implementing the actual position controller. No source modified and no actuation command sent in this review.

Read-only Jetson status at2026-11-06T05:24:26Z:ESP32 connected, bench_state CAT FAULT*, servo_state UNKNOWN. API remains on legacy pin/type metadata. This is not proof of physical closure or a deployed copy of the latest local sketch. Prior source updates were not flashed.

Primary reference: https://github.com/arduino-libraries/Servo/blob/master/docs/api.md — continuous-rotation commands control speed/direction, not target angle.
