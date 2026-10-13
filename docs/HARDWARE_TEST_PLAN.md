# Staged physical validation plan — NONE of these results claimed

For every stage record date, exact board/part revision, wiring photo or diagram, command/build version, logs/measurements, observer and outcome. Stop on unexpected motion, power sag, overheating or sensor fault. No feeding around an animal until prior stages pass. The firmware currently **cannot activate physical outputs**.

| Order/stage | Test | Expected result | Failure symptoms | Precaution | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 Jetson boot | Run `uname -a`, OS, JetPack, Python checks | boots; versions recorded | reset, missing Python | no actuators | terminal output/model |
| 2 Webcam | `tools.test_webcam` on discovered node | frames with measured dimensions/FPS | read errors, unavailable node | no dataset capture | frame report/one temp image |
| 3 ESP32-S3 compile/flash | Select reviewed S3 HW_SAFE USB route (`esp32s3_n16r8_hw_safe_uart` for an identified bridge); explicit upload only after exact board/memory/port review | build/flash/boot recorded | build/upload error | servo/pump disconnected; classic profile is not seller-S3 firmware | build/image hash/log |
| 4 Serial link | PING/GET_STATUS, CRC, unplug/reconnect | correlated replies, offline/recovery | timeout, wrong ID/CRC | USB only, no GPIO UART | protocol trace |
| 5 HX711/load cell | verify tare and known masses, faulty/unplugged behavior | stable calibrated grams, FAULT on errors | drift/timeout | no gate actuator | samples/calibration |
| 6 DS3231 | compare UTC and power-cycle RTC | valid time and day preserved | invalid/rollback | daily limits fail closed | clock logs |
| 7 Food ultrasonic | bounded measurements against known levels | stable readings/timeout fault | 5 V ECHO, bad echoes | level shift verified first | voltage/readings |
| 8 Water ultrasonic | bounded readings with hysteresis | low/high and faults distinguished | false wet/dry | level shift and splash protection | readings |
| 9 OLED | show fault/status with sensor disconnected | legible status, no false HEALTHY | blank/bus error | check I2C voltage | photo/log |
| 10 Buzzer | bounded alert pattern under test | audible fault alert | stuck output | safe sound level | test log |
| 11 Button | press/release debounce | one request per press | bounce/repeated command | outputs still disabled | event log |
| 12 Servo WITHOUT FOOD | only after explicit future safety approval | bounded open/close and stop | stall/overcurrent | dedicated supply, emergency stop | current/motion video |
| 13 Pump WITHOUT ANIMAL | approved isolated water rig | timed filling then off | leak, dry run, stuck MOSFET | protected supply, spill control | runtime/current/level |
| 14 Integrated feeding | weighed dummy material, no animal | limits/cooldown and final outcome | overfeed/no progress | supervision and mechanical stop | grams/time/events |
| 15 Integrated water | controlled fill/drain, no animal | hysteresis/timeouts work locally | overflow/no progress | spill containment | level/runtime logs |
| 16 Camera + sensor fusion | synchronized recorded observations | sessions only with valid evidence | identity/clock mismatch | no automatic actions | correlated logs |
| 17 Cat observation | approved supervised passive study | noninvasive labeled real sessions | distress/inference errors | stop on animal discomfort | consented anonymized metadata |

Each stage requires its own recorded pass. A PC compile or simulator trace never substitutes for an on-device test.
