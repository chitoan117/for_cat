# HX711 physical-reference calibration — measurement only

## Current milestone boundary

SOFTWARE READY. Session `hxcal_91ca4d57d8c24e5d92a3f063a8b01494` is AWAITING_ZERO;
0 physical reference points,0 active models. PHYSICAL CALIBRATION IN PROGRESS
means the workflow is prepared, not that a gram test passed. PHYSICAL PASS,
reference accuracy and real restart persistence are NOT TESTED until the operator
actually places each reference. Servo/pump/arm/AUTO/output remain BLOCKED.
No dispense/actual_dispensed_grams is generated; target remains35g actual added.

## Audit and implementation choice

The reference source used for the previously deployed diagnostic app SHA256
118bfb14cb8adc3fe435857c5dc463cad4874552bba072bab482584158c326a1
contains signed24-bit HX711 channelA/gain128, averaged tare, single-reference
factor and validation commands (1..64 samples). Scale formula is
`(raw-tare_counts)*grams_per_count`. The NVS namespace m4-calibration/key
sensors-v2 stores a39-byte version1 record, flags/double tare/double factor,
food/water geometry floats and CRC16. Firmware grams reject negative values.
Current telemetry says firmware_calibrated=false; actual MCU offset/factor are
not transmitted by the canonical bridge, hence UNKNOWN rather than guessed0.
No NVS readback or write was done. Reference source provenance is an audit,
not a new flash/readback. The real Jetson staged ESP32 source is legacy/conflicting
and must not be flashed as a shortcut.

The existing C++ bridge and SystemState previously intentionally forced gramnull.
This milestone uses **host-side multi-point calibration** on REAL published raw,
separate SQLite records, without serial commands, flash or NVS change. MCU/OLED/
C++ controller calibration remains unchanged; verified host grams are for
SystemState/app/bench measurement, not automatic actuator authorization. The
native arbiter can therefore still say WEIGHT_NOT_CALIBRATED even after host
display calibration: physical-controller integration is a later milestone.

## Storage, formula and validity

Canonical `/home/toan/for_cat/jetson/data/events.db`, additive tables:
- hx711_calibration_sessions: criteria, binding, state, candidate and validation rounds.
- hx711_calibration_points: immutable raw windows, stats/provenance and SHA256.
- hx711_calibration_active: verified model + SHA256; no guessed default factor.

Point raw is deduplicated by increasing MCU report time. Default capture waits5s
then collects30s; >=25 inliers and>=25s span are required. Published JSON is~1Hz;
this is not every native10/80SPS conversion. Isolated Hampel/MAD outliers may be
removed up to10%, with original values/indices retained. Consecutive anomalies,
excessive outliers, rail counts, stale reports, unsafe flags or restart during
a point abort it. No long database transaction is held during collection.

Fit requires0/5/10/20/30/35g. Let r0 be robust zero mean, ri each loaded mean, mi
the nominal mass. `counts_per_gram=sum(mi*(ri-r0))/sum(mi*mi)`;
`grams_per_count=1/counts_per_gram`; grams=`(filtered_raw-r0)*grams_per_count`.
Negative raw slope is valid if increasing load still produces increasing grams.
Fit checks monotonicity, noise/drift, resolution and residual at all references.
Candidate values are diagnostic `candidate_grams`; canonical grams staysnull
until an independent validation round and explicit activate succeed.

Live SystemState uses10 distinct reported samples, at least8s span; gaps/reboot
reset the window. Gram values are filtered window estimates with STABLE/UNSTABLE,
not a final weight from one sample. Unknown/stale/candidate/invalid checksum/
binding mismatch/outside validated range hides grams. Small signed zero noise
within tolerance is visible rather than silently clamped to0.

Binding uses the identified USB serial/mode/HX pins and audited ADC profile.
HX has no unique load-cell identity. Wiring, load cell, mechanics, ADC gain/channel
or firmware changes require a new calibration; mode/USB checks cannot detect
every such external change. Other Meal Plan/config edits do not erase coefficients.

## Proposed strict bench acceptance

These are agreement targets against operator nominal reference weights, not a
certificate of metrology accuracy. Load-cell rating/reference uncertainty are
currently unknown. No tolerance is widened automatically to obtain PASS.

| Reference | Absolute error limit |
|---|---|
|0g/return zero|0.10g|
|5g|0.10g|
|10g|0.10g|
|20g|0.20g|
|30g|0.30g|
|35g|0.35g|

Additionally: peak-to-peak<=0.20g, sigma<=0.05g, first/last-half drift<=0.10g,
consistent signed load response, complete independent validation and unchanged
coefficient identity after restart. Coarse resolution/noisy low-mass response
must be reported as limitation/BLOCKED.1/2/3g are available small references but
not separately certified by this primary0/5/10/20/30/35g protocol.

## Operator physical sequence

**STOP after TEST0 now. Later steps below are a procedure, not executed results.**
Keep the normal installed pan/mechanics as the tare baseline, remove all test
weights/food and hands, avoid table movement, cable tension and load-cell contact
with surrounding supports. Record load-cell capacity/label when available.

Use the existing isolated Python3.11, not Ubuntu's Python3.6:

```sh
PY=/home/toan/for_cat/.venv/jetson-integration/bin/python
TOOL=/home/toan/for_cat/jetson/tools/hx711_calibration.py
SID=hxcal_91ca4d57d8c24e5d92a3f063a8b01494
```

### TEST0 — first action requested now

Remove all reference loads; keep the tare baseline fixed. Run:

```sh
"$PY" "$TOOL" capture --session "$SID" --phase fit --mass-g 0
```

Hold still for approximately35s. Output includes unique sample count, raw mean/
spread/noise/drift, rejected indices and tare_candidate_counts. **grams remains
null because no valid scale exists yet.** Send that JSON for review; do not claim
zero/gram PASS from a single value and do not proceed to servo.

### Later FIT points — only after zero review

Place each reference centrally, replace rather than accumulate unintentionally,
hold still and run the corresponding command separately:

```sh
# place exactly5g
"$PY" "$TOOL" capture --session "$SID" --phase fit --mass-g 5
# replace with10g
"$PY" "$TOOL" capture --session "$SID" --phase fit --mass-g 10
# replace with20g
"$PY" "$TOOL" capture --session "$SID" --phase fit --mass-g 20
# place20+10=30g
"$PY" "$TOOL" capture --session "$SID" --phase fit --mass-g 30
# place20+10+5=35g
"$PY" "$TOOL" capture --session "$SID" --phase fit --mass-g 35
"$PY" "$TOOL" fit --session "$SID"
```

Inspect candidate offset/factor, residuals and gram-scaled noise. This is not
physical accuracy PASS yet. Failed point raw evidence is retained; a short/
unstable capture is not accepted by widening tolerance. A new fit invalidates
old validation rounds and active authority.

### Independent VERIFY round

Remove/reposition references for NEW captures, not a replay of FIT data. Capture
0,5,10,20,30,35,0 in order, replacing the weight before EACH command:

```sh
"$PY" "$TOOL" capture --session "$SID" --phase verify --mass-g 0
"$PY" "$TOOL" capture --session "$SID" --phase verify --mass-g 5
"$PY" "$TOOL" capture --session "$SID" --phase verify --mass-g 10
"$PY" "$TOOL" capture --session "$SID" --phase verify --mass-g 20
"$PY" "$TOOL" capture --session "$SID" --phase verify --mass-g 30
"$PY" "$TOOL" capture --session "$SID" --phase verify --mass-g 35
# remove all reference weights, return to zero
"$PY" "$TOOL" capture --session "$SID" --phase verify --mass-g 0
"$PY" "$TOOL" validate --session "$SID"
"$PY" "$TOOL" activate --session "$SID"
```

Only a fully passing round can activate. Canonical grams then become available
after the live window fills; state CALIBRATED_PENDING_PERSISTENCE, not full physical
milestone PASS. A failed verification round stays in evidence. To explicitly
repeat the WHOLE independent round before activation:
`"$PY" "$TOOL" reset-phase --session "$SID" --phase verify`.

### Restart persistence — operator action required later

Save/record model ID, offset and factor using `status`. Operator resets ESP32 or
reboots Jetson after activation; no flash is required. After REAL raw recovers,
capture NEW0/35/0 with phase persistence (replace/remove real weights accordingly):

```sh
"$PY" "$TOOL" capture --session "$SID" --phase persistence --mass-g 0
"$PY" "$TOOL" capture --session "$SID" --phase persistence --mass-g 35
"$PY" "$TOOL" capture --session "$SID" --phase persistence --mass-g 0
"$PY" "$TOOL" finish --session "$SID" --confirm-physical-tests
```

Finish requires observed host-boot or MCU-boot change AFTER activation, passing
fresh reference/return-zero captures and explicit operator confirmation. Merely
restarting API is useful for SQLite reload but does not satisfy this physical
restart gate. To redo a failed persistence round, use reset-phase persistence;
earlier raw files stay intact. No restart or reference placement is automated.
Missing/failed persistence is NOT TESTED/BLOCKED, never inferred PASS.

## API/UI and safety

`GET /api/hx711/status`: hx711.raw/raw_counts, grams, calibration_state,
calibration_valid, stable/stability_state, tare_offset_counts, grams_per_count,
counts_per_gram, raw_window_samples/span, spread/stddev, sampled_at/age_seconds.
Age refers to source telemetry, not an invented exact ADC conversion timestamp.
`GET /api/hx711/calibration`: criteria, latest session/point summaries and active
metadata; both routes are READ-ONLY. /api/status and existing WS use the same
weight object. All calibration mutations are explicit local operator CLI calls.

No scale coefficient is defaulted to1 and no zero is fabricated. Candidate gram
diagnostics are named candidate_grams; actual_dispensed_grams remainsnull in all
measurement responses. Host grams do not promote MCU calibration, C++ arbiter
authorization, EATING or consumed grams. Scheduled Worker/Meal Plan/preview and
existing AI continue unchanged. No serial TX, NVS write, servo or pump calls.

## Evidence and regressions

Primary folder: evidence/hx711_calibration_20261026T041547966931Z/.
Session physical/SESSION_ID receives full raw/point JSON, hashes and command
metadata. SQLite retains raw windows/round identities; active model integrity is
SHA256 (integrity metadata, not a cryptographic operator signature). Original
source/DB/firmware-reference audit, safety snapshots and regression logs retained.
Prepared physical gram/restart evidence remains empty/NOT_TESTED until execution.

Software checks:428 backend tests including29 calibration cases and existing
worker suite, M4/HX fake-I/O3351 assertions under UBSan, existing fake dispense
9/99+9 checks, pip/diff PASS. Flutter analyze clean/34 tests/release PASS; actual
browser/API verify real raw and null grams/coefficients with0 physical points.
Synthetic fixture state-machine tests are NOT real physical calibration results.
No firmware/C++ model/engine changes.36 staged files/index protected.
