# Servo unloaded test — LATER GATE ONLY, no enablement in this pack

Prerequisites: M3, sensor/RTC/accessory evidence, verified servo GPIO/signal level, power tree and mechanical endpoints; separately approved bounded actuator-test firmware. `ACTUATOR_OUTPUTS_ENABLED=0` currently prevents physical output; there is no servo command/test driver. Do not simply remove the guard.

Future connections: adequate **external** MG996R supply/return wiring, common signal reference ground where required, verified signal translation, safe power disconnect. ESP32/Jetson logic rail or GPIO must not power the servo. Initially no food, no gate/load or animal; secure the mechanism so movement cannot trap fingers.

Commands: **none runnable for actuation now**. After future reviewed test image, run only its explicit bounded unloaded-motion test and serial monitor; hash/record that image. No raw servo REST endpoint is allowed.

Future test: safe/off boot and reset → small controlled motion inside verified endpoints → closing confirmation → current/inrush and MCU/Jetson brownout observation → mechanical endpoint assessment → safe simulated jam/timeout → bounded stop and power-loss behavior. Do not force a stall or choose production angles from another mechanism.

PASS: repeatable unloaded motion/closure, declared current/temperature bounds, no logic resets and proven timeout/off behavior. FAIL: jamming, runaway PWM, overcurrent/heating, endpoints forced, reset or unknown closure. Save wiring/voltage/current trace, video, timing/logs and safety-stop result in `evidence/servo/`. Next gate: isolated pump test; integrated food is still prohibited until both subtests and mechanism review pass.
