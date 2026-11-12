# Water-level sensor (JSN-SR04T candidate) — M4, NOT SENSOR VERIFIED

> **Current command availability:** `diag_water_sensor` exists and reports raw/filtered distance and hypothetical policy requests, physical pump OFF. Use `M4_DIAGNOSTIC_COMMANDS.md`. Earlier absent-tester wording is HISTORICAL / NOT CURRENT for diagnostics; no physical water/pump result is asserted.

Prerequisite: actual JSN board revision/interface mode, trigger/echo voltage, blind-zone spec and mounting identified; protected ECHO and approved bounded sensor-only firmware. Current HW_SAFE has no physical water driver. Pump/servo remain disconnected.

Connections: power off, reviewed VCC/GND/TRIG/ECHO with level translation where required. Waterproof transducer does not make the controller PCB waterproof. Keep electronics dry and splash protected; test water geometry independently.

Commands: no current `test_water_sensor` executable exists. After approved test image/driver, monitor raw echo/distance/validity (`pio device monitor --port ACTUAL_COM --baud 115200`) and save in `evidence/water_sensor/` with image hash.

Test known raw targets before water → actual min/max range and **blind zone** → mounting height/angle and beam reflections in the real container → empty/partial/full calm water → disturbed surface/reflection changes → condensation/splash conditions within safe design → invalid/missing echoes/timeout → filtering/hysteresis and calibrated level conversion. Blind-zone readings must not become fake FULL. Identify mounting/surface effects before interpreting echoes as water level.

Use calibrated empty/full geometry only for valid echoes; unknown remains unknown. Later pump integration must use validated low/recovered thresholds, progress/maximum-runtime limits and sensor-fault OFF behavior, independently of Jetson.

PASS: repeatable usable readings under recorded geometry/conditions, declared tolerances and explicit faults/no chatter. FAIL: unsafe voltage, blind-zone/wall echoes, condensation-related false levels or fault treated as normal. Next gate: OLED; pump control is a separate later gate.
