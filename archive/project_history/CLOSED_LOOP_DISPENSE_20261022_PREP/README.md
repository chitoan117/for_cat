# ForCat Phase1 #3 — supervised closed-loop bench, NOT physically verified

**Start:** `CLOSED_LOOP_DISPENSE_BRINGUP.md`. The packaged `firmware.bin` is
**application-only** for a board already flashed with the matching HX-only
bootloader/16MB partitions. No factory image is present: a factoryflash AFTER
load-cell calibration would erase/overwrite NVS calibration. Review the actual
board before applying; this package does not prove what's installed on it.

ESP32-S3 GPIO4 HX711 DOUT,GPIO5 HX711 SCK,GPIO6 servo PWM. GPIO7 pump OFF.
ASCII supervised `dispense` console only; NO JetsonCAT/HC-SR04/Web/MealPlan or
normal binary feed link. The firmware **can move GPIO6 after manual inspection,
configuration and arm**; ordinary `ACTUATOR_OUTPUTS_ENABLED=0` does not make
this deliberately selected bench image electrically inert. Do not run it
without direct supervision, a genuinely calibrated HX711 and verified gate
CLOSE/OPEN positions from the separate physical tasks #1/#2.

Current app image: `firmware.bin` **396256 bytes**, SHA256:
`c8f86884485aed701608a62f1edd12948af547362599c5a5610401313902fe08`.
Deployment offset: `0x10000`; factory image excluded. No board flashed, no
servo/pump actuated, no physical gram/tolerance established by this task.

Software checks:378Python,9 portableC++14 policy cases/99 assertions,
6 actual firmware-loop fakeHX/LEDC/NVS cases/558 assertions,
55 compile guards,23/23 firmwareprofiles,7 UARTvectors,UBSan canary/native PASS.
See `host_checks/summary.json` and `host_checks/dispense-bench-*/` for **synthetic**
traces. These numbers are not evidence of actual food dispensing.

Copy `physical_trial_TEMPLATE.md` into a NEW actual results file and provide the
raw serial log, typed commands, known reference masses, independently weighed
food before/after and servo/scale/video evidence. Keep the original template and
`release_sha256.json` untouched; future logs under `logs/` are new evidence,
not part of this software-only release hash.
