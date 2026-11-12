# Current supervised Servo + HX711 bench V2 — PHYSICAL NOT VERIFIED

**Read `CLOSED_LOOP_DISPENSE_BRINGUP.md` before hardware operation.** Current
`diag_dispense_bench` app:396352bytes SHA256
`25775b3eb0f4d8434d9c6433e8aa8d7a59a24885d92d8abba3e7b1451f2439e7`.
The older `CLOSED_LOOP_DISPENSE_20261022_PREP` artifact is superseded (preserved).

This package intentionally contains **only `firmware.bin`** at app offset0x10000;
it does not include the factory image because that can overwrite the previously
measured HX711 NVS calibration. Match the *actual installed* bootloader/partitions
with the HX-only bundle before flash. If mismatched, STOP. No board/servo/HX was
physically operated or verified by the agent in this task.

This image CAN move GPIO6 after operator `dispense inspect YES`, explicit
configuration and `dispense arm YES`. GPIO4/5 read HX711, GPIO7 pump remains OFF.
No CAT/HC-SR04/Jetson/Web/scheduler input can trigger feeding. All servo
mechanical CLOSE/OPEN and HX711 calibration remain PHYSICAL NOT VERIFIED until
the separate real logs #1/#2 are received. Do NOT treat NVS factor code2 as
physical validation; do not use this image on an unattended rig.

See `host_checks/summary.json` for378Python PASS,23/23firmware builds,55guards,
9 policy cases/99 assertions,6 actual-loop cases/558 assertions under fakeIO,
and UBSan canary. The output examples in host_checks are **synthetic**.
Copy `physical_trial_TEMPLATE.md` to a new file for actual observations; the
published release and its hashes should remain unchanged.
