# FOR_CAT servo-only relative-position fix — 2026-11-06

Owner explicitly chose keeping the existing continuous360-degree servo and accepting relative positions. No fine adjustment, no added endstop/encoder, no fabricated absolute position.

## Implementation

- Existing UNO profile retained: GPIO6,50Hz14bit,OPEN1400us/1100ms,CLOSE1600us/900ms,NEUTRAL1500us held after stopping. GPIO47 remains disabled.
- A completed timed stroke records only a RAM estimate OPEN or CLOSED. Repeated same-direction full manual strokes do not produce extra rotation. Automatic opening cannot add another opening from an estimated OPEN stop.
- Repeated close requests while closing cannot restart/extend the timer.
- STOP/abort during a cycle clears the estimate to UNKNOWN and latches inspection. Button/Web feed no longer silently clears that inspection latch. Manual full strokes also respect the latch.
- `inspect_ok` now explicitly acknowledges the owner's physically aligned CLOSED position, without changing physical_closed_verified to true. `servo_position` prints estimate/feedback/lock/movement/timings.
- Numeric3/open and4/close remain full strokes. Numeric1/2 remain CAT/DOG for Jetson. All fine-adjust commands/constants/help removed from the deployed image too.
- Startup estimate is UNKNOWN and no startup movement is added. As previously, an initial full movement is allowed without a sensor measurement; the owner must ensure a closed starting reference for an opening cycle, especially after power loss. This is not homing.

Relative timing cannot eliminate drift across legitimate cycles when speed/load/supply or neutral behavior varies. Duplicate rejection only fixes command-induced extra strokes. No automatic correction, stall-against-stop move or compensation pulse was added.

## Strict scope and two source baselines

`current/esp32/esp32.ino` updates the actual local main file `D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino`, preserving its already-prepared PCB/water/reference features. Source backup:current/before.ino. Source SHA2560f2c31d906334f05ff8b10b0e02ab595d30b3d2477fe3e5615ce030d29efb0dc.

`deployed/esp32/esp32.ino` is the servo-only delta from the actual previously flashed readiness firmware. This was flashed to honor the owner's request to preserve all other live behavior. It does NOT deploy the separate pending PCB pin/type/percentage/pump/loadcell-reference updates. In particular, the live unrelated near threshold and D2 echo pin remain the pre-existing values20cm/GPIO10. No Jetson API/bridge source was changed in this step.

HX711 driver, conversion/filter and selected calibration/scale/sensor functions are text-identical before/after, recorded in scope_check.json. Timed servo stopping at the existing measured30..40g conditions remains; only servo movement/inspection guards changed. Existing NVS calibration is not imported/replaced.

## Verification and deployment

Both actual candidate source baselines pass extracted-code native tests using fake GPIO:200 alternating cycles, duplicate OPEN/CLOSE rejection with no PWM writes,1100/900ms boundary stops, immediate STOP/inspection recovery, Web/manual feed cannot bypass the lock, normal30g close, close timer not restarted, missing scale block, no fabricated physical closure, millis rollover, PWM failure and ownership guards. No real200-cycle mechanical test was performed.

Arduino ESP32-S3 core3.3.12 builds PASS:current408545 program bytes/33736 globals;deployed393817 program bytes/33680 globals.

Before flashing, actual0..0x150000 flash was backed up and its app matched the exact known previous binary SHA256f0e91dcb650f96e9f494d011c493888211b9658e24a686898693c892ac273c79. Partition table matched and OTA sequences1,0 with valid CRC selected app0. Wrote app0 only at0x10000; esptool verify PASS. New app SHA256d7054e255babead6620ddb9cbb67ebe8ddd080b0c335d10254efce05f79eea89. NVS before/after byte-identical, SHA256a2785037a6aa6fddec5366f88c1a64b96daf461f36c697af6e53249514cf30ce.

New boot banner, STOP acknowledgement and unique servo_position response were observed:UNKNOWN,feedbackNONE,moving0,1100/900ms. API/bridge/AI services active; three consecutive fresh ESP32 status frames advanced. No open/close/feed/pump command was sent by the agent.

Owner then explicitly confirmed "Đã căn đóng" after physical alignment. Through the existing bridge, sent only inspect_ok,start,servo_position,mode. Actual UART logs confirmed owner acknowledgement, estimateCLOSED,feedbackNONE,inspect_lock0,moving0 and exited0/READY. Thus the program is resumed after the owner's alignment; the earlier post-flash demo-stop flag is superseded by owner_alignment.json.

Physical repeatability on the mechanism remains for the owner's next observed open/close test. Nothing in these software checks establishes an actual measured endpoint.

Remote deployment evidence:/home/toan/for_cat/evidence/servo_relative_20261106. Downloaded mirror:deployment_evidence. Includes actual flash backup, source delta, before/after NVS, boot, verification and owner-alignment acknowledgements.
