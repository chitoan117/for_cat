# HX711 + 5 kg load cell bring-up — M4, NOT SENSOR VERIFIED

> **Current command availability:** `diag_hx711` now exists; exact reviewed-pin workflow/commands are in `M4_DIAGNOSTIC_COMMANDS.md`. Older “no tester” wording below is HISTORICAL / NOT CURRENT for diagnostics. Normal binary HW_SAFE still does not acquire/calibrate weight. All physical results remain unverified.

Prerequisite: M3, verified GPIO/logic/power plan, correct load-cell mounting/wire identification and **approved sensor-only test firmware**. Current HW_SAFE source has no real HX711 acquisition/calibration command. It must not be mistaken for a ready sensor tester. Servo/pump remain disconnected.

Connections: power off first; connect reviewed excitation/signal wires per actual load cell/HX711 diagrams and approved DOUT/SCK mapping, with verified digital levels. Do not guess colors. Keep the mechanically mounted cell unloaded/in range, avoid cable strain and board current through signal leads.

Commands/evidence: no runnable `test_hx711` tool exists in this pack. After separately approved bounded HX711 firmware is available, monitor its raw/calibrated/time/fault output with `pio device monitor --port ACTUAL_COM --baud 115200` (or its reviewed test command). Save logs in `evidence/hx711/`, recording exact test-firmware hash; current PING/GET_STATUS cannot supply weight.

Manual test order:
1. Record signed raw counts with no load; verify readiness/timeout and no stuck/rail readings.
2. Measure stability/drift over a recorded window; log mean/spread and environmental conditions.
3. Tare at the actual empty bowl/mechanical configuration; record zero count and mounting state.
4. Place a traceable known mass, wait for stable readings, record loaded mean.
5. Compute **grams-per-count = known_mass_grams / (loaded_mean − tare_mean)**; zero denominator, inconsistent polarity or unstable readings fails calibration. If software uses counts-per-gram, record that inverse explicitly. Never hard-code a factor before this experiment.
6. Recheck several different known masses within the load cell's actual rated/mechanical range, including remove/reapply/tare; record expected, measured, absolute/relative error and repeatability.
7. Unplug/induce a safe sensor fault and require timeout/FAULT and no guessed grams/actuator intent.

PASS: raw/stable/tare/calibration/repeatability/error satisfy the pre-recorded acceptance tolerance and fault handling is observed. FAIL: timeouts, sign/scale inconsistency, drift beyond agreed limit, clipping, overload or fault shown as healthy. Next gate: DS3231, then later measured feeding fusion only after integrated validation.
