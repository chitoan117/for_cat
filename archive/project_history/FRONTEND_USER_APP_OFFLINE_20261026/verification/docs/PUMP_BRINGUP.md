# Pump isolated test — LATER GATE ONLY, no enablement in this pack

Prerequisites: verified electrical/GPIO/power/voltage plan and separately approved bounded pump-test firmware. Current HW_SAFE output is hard-disabled and has no pump-on test endpoint. Do not modify the guard as a shortcut.

Future isolated connections: separately rated pump rail (not the Jetson power path), 3.3 V **logic-level** MOSFET drive with safe gate pulldown, appropriate flyback protection, rated wiring/protection and signal reference ground where required. Verify MOSFET switching at 3.3 V VGS, not only gate-threshold voltage. Electronics dry; contained water/tube rig, no animal. Prevent unintended USB/5 V rail backfeeding.

Commands: **none runnable for actuation now**. Later use only the reviewed image's explicit short bounded pulse/timeout interface; record source/image hash and serial trace, not a raw pump REST endpoint.

Future test: boot/reset pump OFF → short supervised pulse → observe motor noise/current/supply sag/reset → verify stop → leak/dry-run constraints → maximum-runtime and no-progress timeout → sensor-fault OFF → recovery/reset policy. Do not rely on Jetson to stop a pump.

PASS: controlled flow/off-state, no resets/unsafe heating/leaks, declared runtime/progress limits actually stop it. FAIL: stuck MOSFET/output, excess current, overflow/dry run, logic noise/reset or missing timeout. Save current/voltage/runtime/level and leak/photos in `evidence/pump/`. Next gate: separately reviewed integrated feeding and water rigs without an animal.
