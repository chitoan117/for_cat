# Servo button retry regression fix — 2026-11-06

Owner reported that the physical button stopped operating the servo after the preceding servo-relative update.

## Root cause established from real logs

GPIO21 presses were detected. The first OPEN and early CLOSE ran, but that early close had only0.14g delta, so the pre-existing mass-result logic set feed_stageFAULT and cat_inspect_required=true. The preceding servo change made manual/Web feed respect cat_inspect_required. This conflated an unverified serving mass with an interrupted servo movement, permanently blocking the next press after a completed900ms close. Earlier tests missed the exact manual OPEN→early CLOSE→OPEN repetition.

## Minimal fix

Only one expression changed, in servo closing completion:

`cat_inspect_required = USE_CLOSE_LIMIT_SWITCH && !hit_limit;`

In the owner's explicitly selected no-limit-switch/timed mode, a completed full close stroke restores the relative CLOSED estimate and permits another manual cycle. A dose below target still remains feed_stageFAULT and is not reported as a successful meal. The scale driver, filtering/calibration, mass thresholds, full-stroke pulses/timings, duplicate-direction guard, interrupted-motion lock, sensors and pump are unchanged. With an enabled physical close limit, failure to hit the switch still requires inspection.

This does not establish a measured endpoint; all prior relative-position limitations remain.

## Validation

Both current local-source and actual-deployed-source candidates passed extracted-code native tests:30 consecutive physical-button callback sequencesOPEN/early-CLOSE/next-OPEN,4s no-mass timeout allowing another cycle after full close, retained lock after interrupted movement, plus the prior200-cycle duplicate/ownership/PWM/timing/rollover/scale guards. GPIO is fake in these tests.

Deployed ESP32-S3 compile PASS:393817 program bytes,33680 globals. The current main sketch `D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino` was updated with the identical one-expression fix after a hash check; backup/current diff preserved. Source SHA25677b18abd32bf15c3a773ebd133e71275dce6105c69ff0f0ba048896634d29e12.

## Actual flash and runtime

Backed up actual flash0..0x150000; actual old app matched d7054e255babead6620ddb9cbb67ebe8ddd080b0c335d10254efce05f79eea89. Partition table/OTA selection checked. Wrote app0 only, esptool verify PASS. New app SHA256b88c1aa94df1e1a617405a56effd53a4930bc27246db125b26446bc98dc0984b. NVS before/after byte-identical:a2785037a6aa6fddec5366f88c1a64b96daf461f36c697af6e53249514cf30ce. No new loadcell import or recalibration.

New boot banner/servo_position responded stopped. Bridge/API/AI active; fresh status frames advanced. The agent sent only STOP during programming, then start and read-only queries; no movement/feed command. No fabricated physical-closed acknowledgement was sent.

The owner independently pressed the physical button after the update. Actual UART logs at12:49:34/12:49:51 show two OPEN1100ms requests, each followed by a user-requested CLOSE900ms. Both closed with0.12g delta, yet the next opening was accepted. Read-only mode at12:50:03 confirmed timed estimateCLOSED,feedbackNONE,inspect_lock0,moving0 despite retained CAT FAULT* mass result. A fifth button press at12:50:13 opened again; the4s no-mass timeout closed at12:50:19. Thus the actual firmware button-to-PWM command path accepted repeated cycles. Physical mechanical motion still requires the owner's visual confirmation.

An asynchronous question asks the owner whether the servo physically moves through both cycles. Do not infer mechanical success from UART alone.

Owner acceptance received afterward: "Đã chạy lại được cả hai lượt" in response to the requested OPEN→CLOSE→OPEN physical-button test. Physical servo movement through both attempts is therefore owner-confirmed. This closes the button-lock regression; long-term endpoint repeatability and absolute positioning are not established by this short acceptance test.

Remote evidence:/home/toan/for_cat/evidence/servo_button_20261106. Local downloaded mirror:deployment_evidence.
