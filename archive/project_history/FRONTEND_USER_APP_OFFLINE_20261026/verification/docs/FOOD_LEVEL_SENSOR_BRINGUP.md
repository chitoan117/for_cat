# Food-level sensor (HC-SR04 candidate) — M4, NOT SENSOR VERIFIED

> **Current command availability:** `diag_food_sensor` exists with injected pins/range and separate measured geometry; see `M4_DIAGNOSTIC_COMMANDS.md`. Earlier absent-driver wording is HISTORICAL / NOT CURRENT for diagnostics. Normal binary HW_SAFE still does not report measured food level.

Prerequisite: exact module identified, ECHO level protection and GPIO waveform review, geometry/mount known, approved bounded sensor-only driver. No physical ultrasonic driver or command exists in current HW_SAFE; its status does not measure food. Actuators remain disconnected.

Connections: power off; reviewed VCC/GND/TRIG/ECHO with **verified ECHO divider/level shift** before ESP32 input. Avoid shared trigger/echo interference with the future water sensor; test independently first.

Commands: after separately reviewed driver/test image, monitor its raw distance/echo-duration/validity output (`pio device monitor --port ACTUAL_COM --baud 115200`); log to `evidence/food_sensor/` with firmware hash. Do not flash HW_SAFE expecting readings.

Test raw distance to known targets → measured min/max usable range/dead zone → filtering over logged samples → invalid/missing/out-of-range echoes and timeout → actual empty/part-full/full container geometry (surface slope, walls, hopper reflections) → calibrated conversion and hysteresis. Nominal internet range numbers are not your usable range.

For a reviewed distance-based geometry, conceptual level fraction `(D_empty − D_measured)/(D_empty − D_full)` is valid **only** with distinct calibrated empty/full distances and valid echoes; invalid data stays unknown, not clamped to fake full/empty. Choose filtering/hysteresis from measured variability; verify repeated transitions/no chatter.

PASS: raw/filtered accuracy meets declared tolerance in the real hopper and faults are explicit. FAIL: unstable/wall reflections, ECHO voltage unsafe, chatter, range invalid or missing echoes reported healthy. Next gate: water-level sensor; dispense action still prohibited.
