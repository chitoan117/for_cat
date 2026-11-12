# Safety decision — APP FLASH NO-GO / SERVO-PUMP LOCKED

Date: 2026-10-30. Read-only/identity review only; no new physical gate self-approved.

## Gates that can be retained/closed from existing file evidence

| Gate | Classification / scope |
|---|---|
| Phase4 offline package integrity/source identity | VERIFIED_PASS local bytes; no new hardware qualification |
| Sensor image400304 bytes/SHA a6ad4b3f…ebb4b56 | VERIFIED_PASS local rehash this session; remote prior MATCH OWNER_CONFIRMED |
| Rollback app381984 bytes/SHA820cdeec…3a4b9826 | VERIFIED_PASS local rehash; real restore NOT_RUN |
| A/B16MB matching backup, SHA56a04d58…6d9a8e16, partition/layout analysis | Prior VERIFIED_PASS carried forward via accepted receipt; no third device read or backup rewrite |
| R1 GCC7.5 ARM64/whole Bridge/115ROI/17session/26replay | OWNER_CONFIRMED prior PASS retained; exact remote file not read now, no retest |
| HX711 static accuracy accepted35g34.981g | OWNER_CONFIRMED scoped physical PASS retained; no full weight-series/tare/refit repeat |
| Assembly completed / Jetson powered | OWNER_CONFIRMED; not electrical proof |

## Remaining APP-only flash blockers — short authoritative list

1. **Current running partition/board/boot binding:** no actual app/boot evidence this session. OTA-derived app0/0x10000 is not runtime proof. Do not reset just to fill this gate without maintenance approval.
2. **Current security/eFuse/anti-rollback policy:** missing decoded board-bound values and compatibility of old/new images/secure_version0; no ROM/security read approved. No fuse writes or missing=disabled inference.
3. **Electrical:** individual ECHO13/17/15/10 protection and numeric HIGH-peak evidence, actual schematic/wiring, common ground/stable supply. Never5V ECHO direct to ESP32-S3; DMM average is not pulse-peak proof.
4. **Load isolation / emergency cutoff / HX RAM-loss ACK:** physical servo/pump/buzzer load-power isolation, safe power/current/driver conditions, reachable cutoff and explicit acknowledgement that reset/USB/ROM/APP restore does not restore RAM tare/calibration.
5. **Reviewed executor + recovery/handback + separate approval:** exact USB/sole owner, qualified ROM/write/verify route and usable BOOT/RESET/rollback feasibility; old app valid bytes do not prove hardware recovery. Need specific flash approval; no bootloader/table/NVS/otadata changes.

Additionally, current target identity/resources/serial-owner preflight is BLOCKED_AUTH and hardening ARM64 is NOT_RUN. These are host/integration qualification gaps, not substitutes for the five physical/flash gates above.

## Actuator-specific gates

- Servo: exact GPIO/image/default OFF; rated isolated supply/current headroom/common GND, clear unloaded mechanism and reviewed safe pulses. ARM itself can move. Pump load OFF/isolated. Separate movement approval under supervision.
- Pump: exact module/driver/voltage/current/protection, measured OFF polarity/boot-reset bias, conditional active image approval, primed water and safe outlet. Servo OFF/isolated. INERT/high-Z is not measured OFF. Separate timed-pulse approval.
- Closed-loop food test: servo/HX/recovery gates PASS, physical settling/inertia policy and separate food-dispense approval. Aim35g, final30–40g inclusive; >40g FAULT/TARGET_OVERSHOOT; mass alone/ACK is not COMPLETE.

## Approval boundary / next physical evidence request

USER should supply existing board-bound boot/security evidence if available; four ECHO protection photos/schematic and each measured peak+method; servo/pump supply/driver model and load-isolation/cutoff confirmation; RAM-loss acknowledgement. Do not dismantle the whole system or repeat accepted HX weights/OLED proof.

If a gap requires Serial/ROM/reset or stopping Bridge, first review a distinct maintenance scope from `maintenance_readiness/MAINTENANCE_PLAN.md`: exact commands, prerequisites, risk (reset/RAM loss/production interruption), bounded stop/normal-boot/handback and expected raw evidence. **Stop for USER-specific approval before execution.** Existing read-window approval does not authorize flash or actuators.

No service changes, serial/camera opens, resets, flash/erase, DB writes, feed/manual commands or actuator requests performed. **APP FLASH=NO-GO; SERVO/PUMP=LOCKED; MANUAL BUZZER=DISABLED.**
