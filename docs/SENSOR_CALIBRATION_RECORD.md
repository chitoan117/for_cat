# Sensor calibration record v1

Implementation: `esp32/include/m4/{calibration,calibration_record,arduino_io}.h`. Portable codec is host-tested; Preferences adapter is ESP32-S3 compiled; **real NVS durability/retention is not verified**.

Namespace `m4-calibration`, key `sensors-v1`, exactly **39 bytes**. This is separate from the existing safety-counter/inspection-latch storage. No migration/overwrite of safety state occurs.

| Offset | Bytes | Meaning |
| ---: | ---: | --- |
| 0 | 3 | ASCII `M4C` |
| 3 | 1 | Version 1 |
| 4 | 1 | Bit0 HX711 tared, bit1 HX711 calibrated, bit2 food geometry calibrated, bit3 water geometry calibrated; high bits reserved/zero |
| 5 | 8 | HX711 tare counts, little-endian double |
| 13 | 8 | Signed grams-per-count factor, little-endian double |
| 21 | 4 | Food full distance, little-endian float |
| 25 | 4 | Food empty distance, little-endian float |
| 29 | 4 | Water full distance, little-endian float |
| 33 | 4 | Water empty distance, little-endian float |
| 37 | 2 | Existing CRC16 algorithm over bytes 0–36, little-endian |

Encoding copies explicit numeric fields rather than serializing a C++ structure/padding. Host/ESP32 numeric layout is double64/float32. Version, magic, flags, length, CRC, finite values and calibration invariants are validated. A rejected portable decode does not alter its destination; the NVS loader deliberately starts with an empty record so missing/corrupt storage leaves no usable factor.

HX711 requires signed 24-bit-range tare, an explicit positive known reference mass, finite nonzero signed factor and a captured tare. Formula: `(raw - tare_counts) * grams_per_count`. Factor sign follows wiring/mount response; no default factor is invented. Tare invalidates a previous factor. Negative/nonfinite or >100000 g results are invalid; the upper bound is an implementation sanity bound, not rated load-cell capacity.

Each level geometry independently requires `0 < full_cm < empty_cm`; formula `100*(empty_cm-distance_cm)/(empty_cm-full_cm)`, clamped to 0–100 **only after** distance validity and explicit sensor-range checks. Percentage is level fraction under that geometry, not volume, food mass or water consumed.

Unset fields must be zero, with flags clear. Loading an empty record means NOT_CALIBRATED when raw sensing is available. Measured parameters become persistent only on `save YES`; startup and ordinary polls never write sensor calibration. `load` replaces in-memory calibration. Saving requires at least one valid calibrated component in the diagnostic UI.

Portable tests cover empty/configured records, positive/negative scale response, invalid reference/tare/geometry, round-trip separate food/water fields, every-byte corruption, atomic decode, unknown version with recomputed CRC and nonfinite data. Hardware follow-up: explicit save/reboot/reload/revalidate, missing/corrupt storage handling and interrupted-write behavior. Store board/module/load-cell identity, mounting, reference-mass provenance, date, errors and tolerances alongside real evidence; v1 stores numerical parameters, not those metadata.

## Physical calibration worksheet — blank, NOT EXECUTED

Copy this template into a real bench record when hardware arrives. It is separate from the numerical NVS record above. Blank entries mean no evidence, not a zero measurement. No tolerance or PASS result is prefilled.

| Session field | Actual value to record |
| --- | --- |
| Date/time, operator, evidence/log paths | — |
| Exact board, sensor/module, load-cell ID/rated capacity | — |
| Firmware environment/revision and reviewed GPIOs | — |
| Supply/logic voltage, grounding, mechanical mounting | — |
| Environment: temperature, humidity if known, vibration, warm-up, mounting/orientation | — |
| Reference value/unit and reference-mass/distance provenance or uncertainty | — |
| Empty/tare average; known-mass raw average; grams-per-count factor | — |
| Food full/empty distances; water full/empty distances (separate) | — |
| Averaging count/filter, trial count, intervals | — |
| Acceptance requirement/tolerance and justification | UNDEFINED — do not invent |
| Notes: drift, return-to-zero, faults, reboot/load behavior | — |
| Overall PASS/FAIL | NOT_EVALUATED — physical test not run |

One row per independent trial; preserve repeated readings rather than just the best result:

| Trial / component | Reference value + unit | Measured value + unit | Absolute error | Relative error (%) | Repeatability group / readings | Environment | Notes / log timestamp | PASS/FAIL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — | NOT_EVALUATED |

For mass/distance with a positive reference, absolute error is `abs(measured-reference)` and relative error is `100*absolute_error/reference`. At a zero reference (empty scale), relative error is **N/A**, not fabricated; record the absolute residual. For percentage, distinguish percentage-point error from a relative error. Repeatability may record all readings, min/max range and sample standard deviation with units and trial count; no repeatability threshold is supplied. Include unloading/retare trials and repeat measurements after save/reboot.

PASS/FAIL is a future judgment against a stated, justified requirement. Until both real data and acceptance criteria exist, retain NOT_EVALUATED. A saved factor, CRC-valid record or HEALTHY driver status alone is not an accuracy PASS.
