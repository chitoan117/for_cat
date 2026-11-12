# ESP32 HX711 golden-reference port — software ready, physical NOT_TESTED

## Latest physical closeout — owner stopped at35g

The original software/build readiness record below predates physical testing.
Current authority is `physical/PHYSICAL_PROGRESS.md`, section15: **5/10/20/35g
loaded-mass demo windows PASS** under owner±.70g accuracy/stability acceptance;
**38g NOT_TESTED, cancelled by owner**. Final signed empty mean−.455779g and the
progressive zero-bias trend are retained; strict zero stability/full physical
calibration/persistence PASS is **not** claimed. Diagnostic coefficients were
RAM-only. Sequence is **CLOSED_AT_35G_BY_OWNER**; no further physical action is
pending. Original build hashes and dated evidence remain unchanged.

## Authority / provenance

`reference/README.md` marks **PHYSICAL_VALIDATED_ARDUINO_HX711_REFERENCE**.
Full 307-line Arduino code was read and archived before ESP32 edits; all 791 serial-log lines were read and a byte-identical log copy retained. Original files remain untouched. Arduino validation is owner evidence for that setup/algorithm; no ESP32 physical result is inferred.

Owner authority for this port: HX711/load-cell board supply **5V**, ESP32-S3 DOUT **GPIO4**, SCK **GPIO5**. No pin-map change. Servo/pump remain **LOCKED**.

Actual working firmware tree:
`D:\for_cat\FULL_HARDWARE_INTEGRATION_20261027\guard_tuning\esp32`.
Root `D:\for_cat\esp32` has an identical pre-port HX711 reader but an older NVS implementation (`sensors-v1`). The current guard tree uses `m4-calibration/sensors-v2`; it is the port target. Do not deploy the older root tree over current hardware.

## Differences found — software mechanisms, not proven electrical root causes

| Aspect | Arduino reference | Pre-port ESP32 | Change / interpretation |
|---|---|---|---|
| ADC decode | Signed 24-bit | Already correct signed 24-bit | Retained fixed-width arithmetic; tested positive/negative boundaries |
| Channel/gain | 25 pulses, A/128 | Already 25 pulses, A/128 | Retained; no evidence gain selection was wrong |
| Clock protection | `noInterrupts`, 1us phases | ESP32 `portENTER_CRITICAL`, 2us phases | Retained ESP32 spinlock and bounded pulses; 2us is not identified as a defect |
| Ready timeout | Busy wait, >500ms per conversion | Nonblocking poll, >=500ms | Retained nonblocking architecture and timeout; fault clears partial groups |
| Mass input | Median of 3 consecutive conversions | One raw conversion per grams update | New independent triplets reject a single spike; no long rolling average |
| Display response | >=1g immediate; otherwise alpha .40 | No equivalent display filter | Dedicated display output with exact golden thresholds |
| Near zero / negative | .20g deadband and small-negative display clamp | Existing control conversion rejects any negative grams | New signed diagnostic measurement exposes negative zero offset; only display is clamped |
| Tare | Explicit 15 raw samples, retains slope | Existing calibration tare invalidates slope | Added explicit `tarePreservingFactor`; old calibration tare semantics retained |
| Error words | Reject 0/-1 | Previously only ADC rails rejected | Reject 0/-1 plus both ADC rails, invalidate readings and abort averaging |
| Calibration source | Hardcoded historical pair | ESP32 calibration/NVS | ESP32 NVS still default; historical pair only on explicit RAM diagnostic command |
| Output cadence | Every completed triplet | Combined diagnostic reports at 1Hz | New HX711-only image reports each triplet and invalid-data heartbeat |

Missing median/display filtering can worsen noise/transient appearance; different tare/calibration/negative-value semantics can make zero behavior differ. These findings do **not** prove the previous multi-gram zero shift was a software acquisition fault or eliminate mounting/power drift. No physical refit was performed.

## Ported pipeline and adaptation

1. GPIO4 input/no pull, GPIO5 output initially LOW; acquire at most one ready conversion per loop.
2. Decode 24 MSB-first data bits, short 25th pulse selects channel A gain128. Readiness waits never occur inside the critical section.
3. Invalid words (0/-1/rails) and ready timeout produce invalid readings; partial median/average/display history is discarded. A recovery needs a fresh full triplet.
4. Three consecutive valid raw conversions form one non-overlapping median; raw telemetry/15-sample tare still uses individual unsmoothed raw conversions.
5. `measurement_grams = (median_raw - offset) / scaleFactor`, where `scaleFactor = 1 / persisted_grams_per_count`. Signed, no deadband/smoothing, no autozero.
6. `display_grams`: strict .20g deadband, golden `(-.5,0)` display clamp, >=1.0g immediate step, otherwise `.40*current + .60*previous`, then display deadband again.
7. The original nonnegative `grams` control interface remains nonnegative and unsmoothed, now using the median input. No display clamp enters calibration or control decisions. Consequently a negative diagnostic mass can be valid while legacy control `health` is DEGRADED; use `measurement_grams`/`valid` to inspect signed drift.
8. `t`/`T` explicitly collects **15 valid raw conversions**, using the existing int64 accumulator/double average; keeps the slope. Any fault aborts the entire tare rather than accepting a partial average. It is RAM-only and never automatic. The arithmetic mean retains fractional counts instead of Arduino integer truncation.
9. A large change appears at the next complete median triplet: approximately 300ms at 10SPS or 37.5ms at 80SPS, plus loop/serial overhead. Per-triplet output is compact JSON plus the Arduino-style display line (tested <350 bytes), within the UART115200 budget at 80SPS/3. Full metadata is emitted by `status` or invalid-data heartbeat. Hardware rate/latency has not been measured on ESP32.

## Calibration and persistence

- Boot and `load` read the **existing** `m4-calibration/sensors-v2` record with the existing codec/CRC. Missing/corrupt/un-calibrated records produce `NONE` and null grams.
- Historical `offset=-668483`, `counts_per_gram=-1064.4473` are **not** fallback defaults. `reference CONFIRM` selects them explicitly as `ARDUINO_REFERENCE_RAM_ONLY` for diagnostic comparison.
- `esp32-cal OFFSET COUNTS_PER_GRAM CONFIRM` accepts an already established owner-supplied ESP32 pair in RAM. This command does not fit from test weights or imply physical validation.
- `t` changes only RAM offset with the current slope. `load` or reboot restores the persisted ESP32 record. **No NVS write command exists in this minimal diagnostic**; the existing combined firmware's persistence operations/schema remain unchanged.
- No old failed HX711 validation point/session/report is removed, changed, activated or refitted. The new diagnostic does not claim to activate the earlier host calibration candidate.

## Exact files changed

Under the working firmware tree above:

- Modified `include/m4/hx711.h` — median, signed/display outputs, error rejection, explicit slope-preserving tare.
- Added `include/m4/hx711_reference.h` — median/formula/reference display helpers.
- Modified `platformio.ini` — added isolated `diag_hx711_reference`, source-filtered to the new diagnostic file.
- Added `src/hx711_reference_diag.cpp` — HX711-only UART0 diagnostic, no other sensor initialization.
- Added `test/hx711_reference.cpp`, `test/hx711_reference_loop.cpp` — focused algorithm/actual-loop tests.
- Modified HX711 cases in `test/native_drivers.cpp` and added `--hx711-only` selection for the existing regression.

Evidence/build outputs are under `D:\for_cat\HX711_REFERENCE_PORT_20261028\`: this report, `verify.py`, `result.json`, `reference/`, compile/test/build logs, `native/` test executables, `firmware/` build artifacts.

Prior guard manifest remains historical and untouched. Against that recorded baseline, only the three existing files listed above differ; **57 other baseline source files retain their hashes**. Other firmware modules, pin map, actuator sources, calibration schema/codec/NVS implementation, old `host_release/` images and old evidence remain unchanged. The root firmware checkout, frontend/backend/AI were not edited.

## Verification actually performed

`D:\for_cat\.venv\Scripts\python.exe D:\for_cat\HX711_REFERENCE_PORT_20261028\verify.py --build`

| Check | Result |
|---|---|
| Golden-code normalized text and serial-log SHA comparison | PASS; original code differs only by final newline |
| Focused driver/reference tests | PASS, 14261 assertions (includes individual fake GPIO checks) |
| Actual new diagnostic setup/loop with fake Arduino/NVS | PASS, 96 assertions |
| Existing native regression, `--hx711-only` | PASS, 894 assertions |
| Host compilations (`-Wall -Wextra`) | PASS, no emitted warnings |
| `diag_hx711_reference` real ESP32-S3 Arduino build | PASS |
| Existing `diag_four_ultrasonic` shared-driver compile compatibility | PASS |
| ESP32 flash / physical calibration / physical response | **NOT_PERFORMED / NOT_TESTED** |

Tests cover signed24, exactly25 clocks, critical-section balance/LOW completion, ready timeout including millis wrap, median spike rejection, zero/5/10/20/35/38g synthetic conversion, .20/1.0/.40 display behavior, signed drift, fault recovery, 15-sample tare/fault abort, no automatic tare, unchanged slope, NVS CRC/load/reboot, unchanged water record, command bounds and rejection. Actual-loop GPIO accounting touches **only4/5**, no PWM attachment, no NVS writes. These are software results, not hardware results.

Initial compilation found an include-order issue in the new file (board target guard before Arduino SDK configuration). Fixed by including `Arduino.h` first, as the existing firmware does; final builds above passed.

## Firmware for MANUAL flash

**Flash this HX711-only image for the next test:**

`D:\for_cat\HX711_REFERENCE_PORT_20261028\firmware\diag_hx711_reference\firmware.bin`

- Application offset **0x10000**, size **381984 bytes**.
- SHA256 **`820cdeecde2c4af7b7b2c7f4a1090a3b5c775809886df662522a44e83a4b9826`**.
- ESP32-S3, 16MB flash, no-PSRAM, bridge **UART0 115200**; existing board/profile settings retained.
- Bootloader/partition hashes match the earlier guard release. Application-only flash on this existing layout; do not erase flash/NVS or use a factory/full-flash image for this test.
- `firmware/diag_four_ultrasonic/` is a separate shared-driver build artifact, not the image requested for the isolated next test. Existing host JSON consumers are not the test interface for `HX711_REFERENCE` output; use Serial Monitor and preserve its full log.

Manual PowerShell example (replace `COMx` with the actual attached port):

```powershell
& "C:\Users\chito\.platformio\penv\Scripts\python.exe" -m esptool --chip esp32s3 --port COMx --baud 460800 write-flash 0x10000 "D:\for_cat\HX711_REFERENCE_PORT_20261028\firmware\diag_hx711_reference\firmware.bin"
```

No flash/serial/network command was executed by the agent.

## Exact physical steps — user must perform

Owner update2026-10-28: known nonzero bench masses now use **±0.70g** demo
acceptance; see `physical/OWNER_DEMO_ACCEPTANCE_20261028.md` and
`physical/PHYSICAL_PROGRESS.md` for current post-restart session/receipt. This
updates acceptance only; original firmware build and historical evidence remain
unchanged. Current offset/slope must stay fixed throughout each mass sequence.

1. Manually flash the application above. Open its UART0 Serial Monitor at **115200**, newline enabled, start saving the full log. Confirm the `HX711_REFERENCE` banner, DOUT4/SCK5, servo/pump LOCKED. Keep the existing owner-confirmed 5V HX711 setup and mounting.
2. With the scale **empty**, leave it untouched for **30 seconds**, send `status`, and keep the pre-tare raw/offset/source/measurement log. This preserves evidence of any existing zero offset instead of hiding it.
3. Default source must reflect the actual ESP32 NVS record. If it is valid and applicable to this mounting, test with it. If absent or not applicable, use **`reference CONFIRM` only for Arduino-algorithm comparison**, or supply an already valid ESP32 pair with `esp32-cal ... CONFIRM`. Do not fit a new slope from these verification weights. Record the selected source. If changing the source, retain an additional empty pre-tare window.
4. If an initial empty tare is needed, send **`t` once** while truly empty. Wait for `TARE_OK` (15 raw conversions) and then a new complete triplet; verify no scale-factor change. Keep **30 seconds** of empty readings. Do not tare between subsequent weights or at the end.
5. Test **0 → 5g → 0 → 10g → 0 → 20g → 0 → 35g → 0 → 38g → 0**. Use known masses. At each placement/removal, retain the transition, allow about3s to settle, then hold untouched for **30 seconds**. Record the true mass and transition time separately; keep all transient/error lines.
6. Judge accuracy/zero drift from **`measurement_grams` before deadband/smoothing**, and display responsiveness/stability from `display_grams`/`KHOI LUONG`. `raw` is the latest individual conversion, `median_raw` the triplet median. `null/INVALID` is a failed/missing reading, not 0g. Large changes should jump on the next completed triplet; record observed latency.
7. Current owner demo acceptance: zero mean within **±0.10g**; known nonzero test-mass mean within **±0.70g** (5g accepts4.30–5.70g); settled-window range≤.20g, sigma≤.05g, drift≤.10g. Accuracy acceptance was relaxed by owner from the historical±max(.10g,1%) rule; retain actual signed error. Checks apply to unsmoothed signed measurements. Do not call a visible deadband zero a validated zero or refit/tare between weights to meet the tolerance. The35g nominal meal target is separately allowed approximate portion variation for the consumption demo; it is not an actual35g dispensing PASS.
8. After the full sequence, keep the final empty window **without tare**. Reboot with the scale empty, record `status` and **30 seconds** of pre-tare readings again. `ESP32_NVS` should reload the original persisted record; any temporary Arduino reference/explicit tare is intentionally lost. Never mistake the RAM reference for saved ESP32 calibration.
9. Return the **full serial log**, image/hash confirmation, calibration source/offset/factor, and placement/removal labels. Only then can ESP32 physical accuracy/zero-return/response/stability be judged. Current physical result remains **NOT_TESTED**.

**ESP32_HX711_REFERENCE_PORT_READY: YES** — software/build readiness only.
