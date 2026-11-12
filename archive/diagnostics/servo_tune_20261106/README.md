# Servo travel calibration — 2026-11-06

Owner reports drift toward OPEN over repeated legitimate OPEN/CLOSE cycles, but no movement while idle15–20s. The preceding duplicate-command and button-lock fixes remain valid; they cannot balance the angular travel of a continuous-rotation servo. No neutral trim, extra correction stroke, feedback sensor or loadcell change is introduced.

## Supervised physical trial

Through the existing bridge, sent only `close_ms 1000`, `servo_position`, `mode`. Actual UART acknowledged close duration1000ms, opening1100ms, moving0. This initially changed RAM only. Owner was instructed to keep ESP32 powered, disconnect only servo power to re-align CLOSED, restore servo power and test5 OPEN/CLOSE cycles.

Owner explicitly replied: **“Đóng về đúng mốc sau 5 chu kỳ”**. See owner_acceptance.json. These are owner-observed mechanical cycles, not an agent-observed absolute angle measurement. Long-term repeatability across varying load/supply is not established by five cycles.

## Accepted profile

- OPEN:right,1400us,1100ms unchanged.
- CLOSE:left,1600us,**1000ms** instead of900ms.
- NEUTRAL:1500us unchanged; owner reports stationary at neutral.
- No fine-adjust or automatic compensating motion.
- Duplicate-direction rejection, complete-close manual retry fix and interrupted-motion lock retained.
- HX711 driver/conversion/filter/calibration and measured mass result unchanged. Native timing-boundary and retry/STOP regression tests pass for both source baselines.

`1000/current` is the local main source update, preserving its already-prepared unrelated PCB features. `1000/deployed` preserves all unrelated behavior of the actual running firmware; only default closing duration and servo help/comments change. Thus pending PCB/pump/backend changes are not silently deployed with servo tuning.

The explicit `servo_uno` command in the local main source still restores the historical1100/900ms reference if deliberately invoked; its help now makes that clear. Normal boot uses the new1000ms default. That command is not present in the deployed baseline and was not sent.

Final build/flash evidence is recorded in deployment_evidence after successful completion. Deployment must match the previous actual app b88c1aa94df1e1a617405a56effd53a4930bc27246db125b26446bc98dc0984b before writing app0, preserve NVS, verify the new app and confirm close_ms1000 after reboot. No movement command is sent during programming/verification.

## Deployment completed

ESP32-S3 build PASS:393817 program bytes/33680 globals. Actual flash backup matched the preceding app, partition table and valid OTA sequences1,0. App0 written and esptool verify PASS. New app SHA2568ceb43f5f4939d75b50e25bef8bd226c91c5eaffb4106959f62aaf90a346113a. NVS before/after byte-identical:a2785037a6aa6fddec5366f88c1a64b96daf461f36c697af6e53249514cf30ce. This persists the new default in the firmware; it is no longer only a RAM trial.

After reset and restoring the bridge, actual UART reported open_ms1100/close_ms1000,feedbackNONE,moving0,inspect_lock0. Start restored exited0/READY. API/bridge/AI all active; three fresh telemetry frames advanced, physical button released. No movement command sent by the agent. Initial estimateUNKNOWN after reboot is intentional and does not claim sensor feedback; owner had just confirmed the closed reference during the physical5-cycle trial.

Local main sketch updated with the servo-profile-only delta, SHA25626b69e947acb8990494f4c52d7a7a93d59b9482fe932da4a14ca71748218a51b. No pending unrelated PCB/backend/pump edits were deployed with this firmware. Actual live source and flash/rollback evidence are under deployment_evidence.
