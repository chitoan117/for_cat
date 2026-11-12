# SERVO bench preparation V2 — physical NOT VERIFIED

**Read `SERVO_BRINGUP.md` first** (copy of current Gitmirror runbook). First
exercise is horn DETACHED, hopper EMPTY, GPIO6 signal, external 5V servo,
appropriate common GND, F5305S/pump unpowered. Confirm the actual servo model
and supported pulse widths before entering provisional CLOSE/OPEN candidates.

`diag_servo_bench` is **not** the ordinary safe diagnostic: it **CAN drive GPIO6
after manual configuration and `servo arm YES`**. It has no CAT/HC-SR04/HX711/Web/
schedule/40g path and cannot enable GPIO7 pump. The old
`SERVO_BENCH_HANDOFF_20261021_PREP` artifact is superseded, preserved for audit;
do NOT flash its earlier factory image.

The source/build was tested with fake LEDC, not real hardware. Seven named host
cases (133 assertions),48 compileguards,22 firmware environments,378 Python
tests, and verified UBSan canary/native checks PASS in the provided summary.
Servo/HX711 **physical tests have not been performed**; the HX711 preparation
from bring-up #1 is not physical validation.

Factory image SHA256 (443552 bytes):
`b96862a9ee1681536a033b52dc2863ead421b73a48d2de546f37390606001a83`.

App SHA256 (378016 bytes):
`53f046e26aa44ce326338048b54122cbf7f83efffe0dd99bed0ebd2dd710a3ab`.

Factory flash covers NVS/gaps: review/backup before applying. No physical
flash or port access was performed here. Copy `physical_observations_TEMPLATE.md`
to a new actual-results file before recording the real run, and send the original
serial RX log/video/photos along with it.
