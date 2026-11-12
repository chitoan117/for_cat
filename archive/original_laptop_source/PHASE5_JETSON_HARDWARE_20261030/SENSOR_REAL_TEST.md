# Real sensors — current integration BLOCKED, no new PASS_REAL

Date: 2026-10-30. Source: actual GET capture `http_lan_20261030/`, analysis `HTTP_ANALYSIS.json`, event log `BRIDGE_EVENTS.json`. Client window `02:29:12–02:29:17Z`, event GET `02:32:53.714077Z`; command receipts/exit codes in `evidence/direct_http/` (0), `evidence/bridge_events/` (0).

## Current pipeline finding

ESP32 → existing Bridge → API does not deliver accepted sensor frames: **ESP32_BAD_TELEMETRY, valid_reports=0, telemetry=null, telemetry_usable_now=false**. Parse errors 641→657 and noise lines645→661 in 4404 ms; oversized_lines=0 in this sample. Existing event log explicitly repeats **unsupported firmware mode**. This is an observed compatibility failure, not proof that physical sensors are broken.

Actual running firmware ID/mode cannot be recovered from the accepted telemetry because it is absent. The known backup contains HX711_REFERENCE, and new quad-sensor firmware is owner-confirmed not flashed; those facts support the mismatch explanation but do not prove current runtime bank/identity. Do not change production parser/mode to conceal it.

## Per-device status today

| Device / intended GPIO | New live test status | Actual evidence / retained scope |
|---|---|---|
| HC-SR04 #1 TRIG12/ECHO13 | BLOCKED | firmware_supported=false; cm=null, valid=false; historical basic-ranging owner evidence retained |
| HC-SR04 #2 TRIG16/ECHO17 | BLOCKED | Same capability/data absence; historical basic-ranging scope retained |
| JSN-SR04T #1 TRIG14/ECHO15 | BLOCKED | Same; no calibrated tank percent/geometry inferred |
| JSN-SR04T #2 TRIG18/ECHO10 | BLOCKED | Same; role TBD, no percent inferred |
| HX711 DOUT4/SCK5 | BLOCKED live integration | raw/grams=null, raw_available=false, calibration_id=null. Prior OWNER_CONFIRMED static35g=34.981g remains PASS; no full weight-series/tare/recalibration required |
| PIR GPIO11 | BLOCKED live integration | motion=null, health UNKNOWN; API owner metadata carries historical physical PASS, not a new live result |
| OLED SDA8/SCL9 | NOT_RUN current observation | API health UNKNOWN; prior owner display evidence retained, no blanket retest request |
| Button GPIO21 active LOW | BLOCKED live integration | pressed/request_count/state_source unavailable/UNKNOWN; historical owner PASS retained |

`wired=true`, `data_source=REAL`, serial-connected or a historical badge do not override invalid/null live measurements. No sensor has new session PASS_REAL. Current GPIO map must still be compared to actual wiring before triggering; do not treat the software map as an electrical measurement.

## Ordered supervised test plan, after corresponding gates/approval

1. Passive metadata/log/GET review now; USER may attach existing original evidence/photos without reset. Do not open another Serial reader or press a button whose current firmware actions are unknown.
2. After reviewed firmware capability, electrical evidence and a specifically approved single-owner maintenance window: capture current HX status/firmware identity without tare/cal writes. Serial open/reset can lose RAM calibration. Existing `serial_evidence.py` execute stops/restores Bridge, so it is **not authorized by the current read-only scope**.
3. With qualified sensor firmware: profile **diag_four_ultrasonic**, wire mode **diag_current_hardware**, candidate frame bound8192. Each ultrasound boots DISABLED; trigger only after its own ECHO protection/peak gate passes. No simultaneous trigger.
4. Freeze module revision/blind zone and error/spread/valid-fraction limits before data. HC1 40→15→40 cm; HC2 three reference points; JSN1/2 three points outside actual blind zone. Three independent windows/point, 20–30 s/plateau. Log every sample, ruler/geometry/timestamp; no cherry-picking. Reuse qualifying old evidence where applicable.
5. Loss of echo by safely moving target should produce timeout/NO_ECHO/null, not valid0cm. OUT_OF_RANGE only if physically observed; otherwise NOT_RUN. Never unplug/short a powered sensor to manufacture faults.
6. Then multiplex three40–60s windows; compare against single-channel results for crosstalk. PIR: firmware warmup≥60s plus actual stability/hold time, timestamp no-motion→motion→no-motion. Confirm OLED/button data through the authorized no-feed firmware path, preserving prior acceptance.
7. HX current-context/freshness is separate from already accepted static accuracy; no repeated initial weights or optimization of0.019g. Closed-loop remains NOT_RUN.

Evidence per device: raw/log hash, UTC plus device/monotonic times, module/pins/units, reference geometry/criteria, null/error/timeout states and USER observations. Outcome PASS_REAL only after reviewed real data; otherwise FAIL/BLOCKED/NOT_RUN. Detailed existing procedure: `..\HARDWARE_PHYSICAL_BRINGUP_20261029\SENSOR_TESTS.md`.

**APP flash alone is not enough for Web:** the prepared full quad frame is roughly4.3KB; historical production4096-byte parser and qualified PIR/firmware-grams gaps need separately reviewed target integration. Current candidate8192 is not deployed. No firmware, Bridge or Web deployment performed.
