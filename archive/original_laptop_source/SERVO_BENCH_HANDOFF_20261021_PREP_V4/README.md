# FOR_CAT servo guarded bench — current V4 handoff

**SOFTWARE/COMPILE PASS, PHYSICAL NOT VERIFIED.** This `diag_servo_bench`
image CAN drive GPIO6 after `servo configure ... CONFIRM` + `servo arm YES`.
The pump, automatic CAT feed and Web commands cannot move a servo in this image.
Do not confuse `ACTUATOR_OUTPUTS_ENABLED=0` (normal firmware policy) with
servo-bench electrical inertness after operator arm.

Read **`SERVO_BRINGUP.md`** first. Its first physical test is horn DETACHED,
feeder unloaded/no food/no cat, 5Vservo separately powered with common signal
ground, pump/F5305S unpowered. Check your actual servo model's pulse interval
before choosing provisional CLOSE/OPEN values. No default physical gate angles.

Prepared factory:443552B SHA256
`b96862a9ee1681536a033b52dc2863ead421b73a48d2de546f37390606001a83`.
App:378016B SHA256
`53f046e26aa44ce326338048b54122cbf7f83efffe0dd99bed0ebd2dd710a3ab`.
Factory flashing can overwrite NVS/gaps. Image was NOT flashed by this task.
Older PREP/PREP_V2/PREP_V3 are superseded, preserved as separate history.

`host_checks/summary.json` reports 378Python PASS, 22/22 PlatformIO profiles,
48 compile guards, 8 real-bench-loop fakePWM cases/151 host assertions, verified
UBSan canary/native process checks. These cannot award physical PASS.

Copy `physical_observations_TEMPLATE.md` to a new file and send the actual
complete serial log/video/wiring photo/servo model/CLOSE/OPEN microseconds,
direction, jitter, ESP32reset and stall observations back for review.
HX711 separately remains PHYSICAL NOT VERIFIED without real calibration logs.
