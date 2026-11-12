# HX711 + Load Cell — actual operator observations

**Physical status: PHYSICAL NOT VERIFIED.** Fill from real readings only.
No reference mass, stability threshold, calibration factor or PASS is prefilled.

## Setup / identity
- Operator / date / time:
- Actual ESP32-S3 model / observed COM:
- ROM chip / detected flash size:
- Firmware profile: `diag_hx711`
- Factory SHA256 used:
- HX711 VCC measured/connected:
- DOUT/SCK: GPIO4 / GPIO5 (confirm actual wiring)
- Actual load-cell rated capacity / type:
- HX711 module / RATE setting if known:
- Load-cell E+/E-/A+/A- identification source:
- Empty-scale configuration (bare platform, bowl attached, etc.):
- Servo and pump power disconnected:
- Received serial logfile(s):
- Wiring / mounting photos:

## STEP A — Empty scale
- Initial `status` / raw_counts / weight_health / weight_reason:
- `tare 16` command time:
- Result `AVERAGE raw=...` (this is tare raw baseline):
- Result `TARE_CAPTURED ...` or actual error:

## STEP B — Zero stability (no repeated tare)
Run `avg 16` one at a time, waiting for each result.

| Repeat | Received time | AVERAGE raw | Observed raw drift/jumps | Health / timeout |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

Add rows as needed. Before calibration grams may be null by design; do not fill0.

## STEP C — Actual reference / calibration
- Exact reference mass (grams):
- How mass was independently established (reference weight/reference scale):
- Exact `cal ... 16` command:
- Loaded AVERAGE raw:
- Exact CALIBRATION result / grams_per_count:
- Fresh calibrated status after next ADC sample:

## STEP D — Validation / remove and reapply
| Repeat | Actual known grams | Exact command | Measured grams | Absolute error | Relative percent | Notes |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

- Unloaded post-calibration raw_counts and grams (copy null if null):
- Any DEGRADED / INVALID_DATA around zero:
- Any additional independently known mass tested:
- Physical stability / accuracy tolerance agreed (leave blank if not yet agreed):

## STEP E — Save / actual reboot (no reflash/tare/cal first)
- `save YES` exact result:
- Reboot method / time:
- Was reference still on platform, or reapplied after reboot:
- Full boot banner:
- CALIBRATION_LOAD code:
- Fresh `status` result:
- Exact validation command after reboot:
- Measured/reference/error after reboot:

## Faults / evidence
- Any AVERAGE_ABORTED / TIMEOUT / FAULT / ADC saturation / save error:
- Any mechanical contact/cable strain:
- Command order if missing from RX logfile:
- Full raw log attached (not screenshots alone):

## Review outcome — leave pending until evidence is reviewed
- Communication:
- Tare:
- Zero stability/usefulness:
- Known-mass calibration:
- Validation/repeatability:
- Persistence:
- Fault behavior:
- Final physical decision: **PHYSICAL NOT VERIFIED**
