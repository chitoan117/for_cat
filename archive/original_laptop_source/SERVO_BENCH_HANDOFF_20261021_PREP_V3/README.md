# SERVO bench preparation V3 — PHYSICAL NOT VERIFIED

Current supervised profile `diag_servo_bench`: after manual configure+arm it **CAN
produce GPIO6 PWM**. It cannot control GPIO7 pump, AUTO feed, MealPlan, Web, or
CAT/DOG. This is not the ordinary disabled normal firmware.

Read `SERVO_BRINGUP.md` for the full preflight, PowerShell flash/monitor commands,
interactive console sequence and physical PASS/FAIL criteria. Do NOT reuse the
previous PREP or PREP_V2 images: those archived bundles are superseded for this
test and retained as history. `deploy_manifest.json` binds this V3 artifact.

Factory:443552 bytes SHA256
`b96862a9ee1681536a033b52dc2863ead421b73a48d2de546f37390606001a83`.
App:378016 bytes SHA256
`53f046e26aa44ce326338048b54122cbf7f83efffe0dd99bed0ebd2dd710a3ab`.
Source and firmware bytes are unchanged from V2; V3 includes additional actual
firmware-loop tests with **fake PWM IO** for u32 time wrap and reset mid-motion, with full UBSan
checks. Latest: 8 bench loop cases/151 host assertions,378Python,48 guards,
22 firmware profiles compile PASS. This is software validation, NOT physical PASS.

First physical test: pump unpowered, no food/cat, servo horn disconnected from the
gate. GPIO6 signal, servo external5V and common ground. Confirm actual servo pulse
range before provisional `servo configure ... CONFIRM`. `servo arm YES` can move the
horn even though the candidate CLOSE is not yet a verified mechanical CLOSE.
External5V/position feedback or a spring/independent interlock is needed before
claiming fail-safe mechanical closure after unexpected MCU/power failure.

`physical_observations_TEMPLATE.md` is blank: copy to a new file for actual run,
send complete serial RX log, command order, video and 5V/hardstop/MCU reset notes.
HX711 remains PHYSICAL NOT VERIFIED without its own physical logs.
