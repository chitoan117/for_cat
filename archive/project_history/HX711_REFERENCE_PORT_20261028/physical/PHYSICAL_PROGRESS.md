# HX711 reference port — physical progress

## Current acceptance addendum — owner correction29/10/2026

HX711 static real-hardware communication/tare/loadresponse/35g measurement vàaccuracy
đã được owner chấpnhận. Hồ sơ scoped hiện hành:
`HARDWARE_PHYSICAL_BRINGUP_20261029/HX711_ACCEPTANCE.json` và `HX711_EVIDENCE_NOTES.md`.
StaticPASS/accuracyacceptedYES/retestNO; persistence vàclosed-loopdispense35g vẫn
NOT_VERIFIED. Latestowner35g=34.981g/error0.019g làlượt khác archived35gmean34.582390
bên dưới; không ghiđè/rawrelabel oldsummary. OriginalartifactsSHA đãreview, giữ
nguyên cảstrictzeronotes. Không yêu cầu lặpweightseries/tốiưu hoặc38g.

## Owner flash / connected device

- Owner screenshot reports app381984 bytes written to0x10000, hash verified, RTS reset completed.
- COM8 is CH343 VID1A86/PID55D3, serial5C85066678.
- Runtime `HX711_REFERENCE` observed on UART115200; local image SHA256 `820cdeecde2c4af7b7b2c7f4a1090a3b5c775809886df662522a44e83a4b9826`. No on-chip binary readback hash was obtained.
- Firmware source/build report remains the historical software-readiness record. Do not replace its original `NOT_TESTED` fields with inferred whole-system PASS.

## 1. Empty before any reference/tare command

Evidence: `20261027T181242105738Z_empty_pre_tare/`.

- Owner confirmed empty; 30.033s,109 distinct median triplets, approximately3.63triplets/s.
- Device calibration `NONE`, `sensors-v2`, `NOT_CALIBRATED`; no calibrated grams. No fallback factor silently supplied.
- Median raw mean−669643.2385counts, range119counts, sigma21.4441counts.
- Offline Arduino-factor projection mean+1.08999g; this is only a historical comparison, not device-calibrated mass or a zero PASS.
- Only `status` sent. No tare/reference/calibration/flash/reset command.

## 2. Explicit diagnostic RAM reference and one initial empty tare

Evidence: `20261027T181614514850Z_initial_reference_zero/`.

- Owner instructed to remain empty throughout. `reference CONFIRM` selected historical slope−1064.4473counts/g and historical offset−668483 in RAM only. It is not production calibration authority.
- Additional **pre-tare**30s:109/109valid triplets; signed mean+1.021549g, range.103340g, sigma.019643g, last-fifth minus first-fifth mean−.003087g. Initial zero offset is retained in evidence; not labelled mechanical drift or silently discarded.
- This pre-tare signal met the established stability checks. Exactly **one** explicit `t` was sent, collecting15raw samples, not refitting the slope.
- Acknowledgment: `TARE_OK OFFSET=-669557.866666667 scale_factor=-1064.447300000 NO_REFIT NO_WRITE`.
- Post-tare source `EXPLICIT_TARE_RAM_ONLY`. Offset−669557.866666667counts, slope unchanged−1064.4473counts/g.
- **Post-tare30s**:109/109valid triplets; signed mean**+.003090g**, min**−.058121g**, max**+.055553g**, range**.113674g**, sigma**.023059g**, window-fifths drift**−.008947g**. Display0.00g throughout, but acceptance uses signed pre-deadband mass.
- **ZERO_WINDOW_PASS=YES**, limited to this empty30s observation and diagnostic RAM pair. Full calibration, loaded-mass accuracy, removal recovery, reboot persistence and long-term drift remain unverified.
- The legacy nonnegative control health reports DEGRADED/INVALID_DATA for a negative mass near zero; signed diagnostic `valid=true` and its actual value remain visible. This does not turn a sensor read error into0g.
- NVS write/refit/servo/pump/reset commands: none. Final status reports both actuator locks and outputs0.
- `initial_tare_once_receipt.json` records command intent before transmission and prevents the helper from repeating an initial tare automatically. Future weight observations must preserve the exact RAM calibration; no repeat tare or automatic calibration reload on drift/reset.

## 3. Owner-declared5g attempt — BLOCKED after RAM calibration loss

Evidence: `20261028T025305241189Z_observe_5g/`, captured `2026-10-28T02:53:05Z`.

- Owner reported placing5g. The agent opened COM8 and sent only `status`.
- Runtime source is now **NONE**, offset/factor null, `NOT_CALIBRATED`, signed/display grams null and `valid=false`.
- Status uptime258925ms (~259s) is lower than the earlier recording's703666ms (~704s), with only ~8h33m elapsed (not a49day millis wrap). This supports a device restart/reset since the earlier observation; exact cause/time is not established. It does not establish that serial opening caused the reset.
- The initial reference and tare were deliberately **RAM-only** and no NVS write was sent. Losing that diagnostic pair across reset is expected; this observation is **not evidence that a previously persisted calibration was erased**. The first baseline already had source NONE.
- Initial latest raw−676348counts and median−676292counts confirm observed loaded raw data, but no calibrated5g reading exists in this attempt. Do not turn those counts or the old zero into a5gPASS/FAIL across an unverified restart/empty baseline.
- The helper stopped after the fresh status (~2.3s), before the planned30s mass window, because the exact expected RAM offset/slope did not match. No automatic tare, reference reload, coefficient change/refit, NVS write, reset or actuator command was sent.
- Previous continuous recorder PID21608 is no longer running; the inspected directory had raw/messages/ready but no final summary. Full placement-transition coverage is not established. Do not claim continuous capture remained active during the8h gap.
- **5G_STATUS: BLOCKED_CALIBRATION_NOT_LOADED. HX711_FULL_PHYSICAL_CALIBRATION_PASS: NO.** The earlier zero PASS remains a historical window only, not a current verified zero.

## 4. Fresh empty raw window after owner removed5g

Evidence: `20261028T025555564568Z_empty_pre_tare/`, `2026-10-28T02:55:55Z` to `02:56:25Z`.

- Owner explicitly confirmed empty. Status-only capture30.052s,109distinct median triplets; COM8 identity unchanged.
- Calibration remains **NONE / NOT_CALIBRATED**. No tare, reference, coefficient change, reset or NVS write was sent.
- Median raw mean **−670968.513761counts**, min−671029, max−670909, range120counts, sigma23.641673counts. No device-uptime backward jump observed inside this window; status uptime428255ms is consistent with continuation of the recent boot seen in the5g attempt.
- Historical Arduino-factor projection: mean+2.335028g, range.112735g, sigma.022210g, window-fifths change+.015165g. Projection is offline only, not actual calibrated ESP32 grams or a zero PASS.
- Versus the previous session's explicit tare offset−669557.866666667counts, the new empty mean is lower by1410.647095counts, equivalent to approximately **+1.325g** using the unchanged historical slope. The zero has shifted between sessions; cause (setup/mounting/loading/power/temperature/etc.) has not been established. A stable30s window does not establish stability across the reboot/session gap.
- The preceding owner-declared5g attempt retained8compact median readings over~1.93s: mean−676306.625counts. Difference against the new empty mean is−5338.111239counts, approximately **5.015g** using the unchanged slope. This is a limited raw-difference comparison, **not a settled30s calibrated5gPASS**, a new fit, or a coefficient sent to the ESP32.
- Raw changes are consistent with removal of the declared5g load, while an inter-session zero shift remains unresolved. Do not retare to erase that shift or call the old zero valid now.

## 5. Owner confirms unchanged scale; new explicitly bounded post-restart session

Owner confirms scale/fixture not touched and considers0.3–0.7g error acceptable
for the continuous-consumption demo. Current acceptance is documented in
`OWNER_DEMO_ACCEPTANCE_20261028.md`; future nonzero bench windows use±.70g
without changing measured values or refitting slope.

Evidence: `20261028T030352777618Z_initial_reference_zero/`.

- A separate new-session receipt `initial_tare_once_after_confirmed_restart_20261028.json`
  was used. The original receipt/session remain untouched. The helper requires
  prior raw baseline proof of the restart and a fresh runtime/host elapsed-time
  match before selecting the reference or allowing one initial tare in this session.
- Same boot as the fresh raw empty baseline was verified: host elapsed479.305s,
  device elapsed478.171s. Initial calibration NONE; no intervening reset inferred.
- Historical Arduino pair selected explicitly in RAM. Pre-tare30s retained109
  valid signed readings, mean+2.407934g, range.116493g, sigma.018193g,
  window-fifths drift−.012079g. This inter-session offset is still recorded;
  zero stability across reboot has **not** been resolved or passed.
- One initial tare in this new boot session: `TARE_OK OFFSET=-671054.666666667 scale_factor=-1064.447300000 NO_REFIT NO_WRITE`.
- Post-tare30s:109/109valid readings, signed mean**+.003614g**, min**−.046660g**,
  max**+.062317g**, range**.108977g**, sigma**.018875g**, window-fifths change**+.010334g**.
- **ZERO_WINDOW_PASS=YES for this session only.** Slope unchanged, no NVS write,
  no actuator/reset command. Final status valid/HEALTHY and both locks asserted.
- Current diagnostic pair: offset**−671054.666666667counts**, slope**−1064.4473counts/g**,
  source**EXPLICIT_TARE_RAM_ONLY**. It must remain fixed during the following masses.
- All subsequent weight commands must select this new receipt explicitly:

```powershell
& "C:\Users\chito\.platformio\penv\Scripts\python.exe" "D:\for_cat\HX711_REFERENCE_PORT_20261028\physical_session.py" weight --port COM8 --mass 5 --session-receipt "D:\for_cat\HX711_REFERENCE_PORT_20261028\physical\initial_tare_once_after_confirmed_restart_20261028.json"
```

The bounded weight helper reads/status only; it verifies this exact RAM pair,
preserves3s settling/transients and observes a30s window. It does not tare,
reload coefficients or refit. Do not use the old-session default receipt.

## 6.5g settled-window check — PASS in the post-restart session

Evidence: `20261028T030939080655Z_observe_5g/`, completed `2026-10-28T03:10:15Z`.

- Owner declared5g placed. Same current-session receipt and exact RAM pair
  confirmed before/after capture: offset−671054.666666667counts,
  slope−1064.4473counts/g, sourceEXPLICIT_TARE_RAM_ONLY.
- Preserved initial/3s settling data, then30s weight window: **109/109valid triplets**.
- Signed measurement mean**4.901414g**, min**4.859173g**, max**4.953118g**,
  range**.093945g**, sigma**.019932g**, window-fifths drift**−.004295g**.
- Mean error**−.098586g** versus owner-declared5g; passes owner demo tolerance±.70g
  and retained stability checks. **5G_WINDOW_PASS=YES**.
- Reference display mean4.901509g, range4.877020–4.924257g. Do not overwrite
  actual measured4.90g with5.00g to present an exact result.
- Commands sent: status twice only. No tare, coefficient reload/refit, NVS write,
  reset, flash or actuator command. Final status HEALTHY/valid, both locks asserted.
- This loaded point is now verified in this session. Removal zero,10/20/35/38g,
  restart persistence and placement-response timing remain unverified.

## 7. Empty return after5g — stable, recorded small signed bias

Evidence: `20261028T031131047971Z_observe_0g/`, completed `2026-10-28T03:12:07Z`.

- Owner confirmed5g removed/empty. Fixed current-session offset/slope/source
  confirmed unchanged before/after observation; commands were status only.
- After3s settling,30s window: **109/109valid signed readings**.
- Signed mean**−.113516g**, min**−.174425g**, max**−.040083g**,
  range**.134342g**, sigma**.023411g**, window-fifths change**+.004429g**.
- Display stayed0.00g, consistent with the reference's±.20g deadband. Actual
  signed bias remains visible and has not been subtracted or hidden in evidence.
- The helper's retained strict zero criterion±.10g reports
  **weight_window_pass=false**, exceeding that mean limit by.013516g. Preserve
  that result; do not relabel this a strict-zero PASS or rewrite the original JSON.
- For the owner's coarse continuous-intake demo, this stable bias lies inside
  the reference zero region and is small relative to the accepted±.70g mass
  accuracy. **Proceed with the demo sequence while retaining this strict-zero
  note**, rather than refitting/re-taring or diagnosing a hardware defect.
- The legacy nonnegative control health reports DEGRADED for these negative
  values, but diagnostic signed `valid=true`; no zero-valued read error has been
  fabricated. Actuator locks remain asserted. No tare, reload/refit, NVS write,
  reset or flash command was sent.

## 8.10g settled-window check — PASS

Evidence: `20261028T031409929796Z_observe_10g/`, completed `2026-10-28T03:14:46Z`.

- Owner declared10g placed. Same current-session receipt and exact RAM pair
  confirmed unchanged before/after capture: offset−671054.666666667counts,
  slope−1064.4473counts/g, sourceEXPLICIT_TARE_RAM_ONLY.
- Preserved3s settling data, then30s window: **109/109valid triplets**.
- Signed mean**9.819718g**, min**9.775339g**, max**9.867406g**,
  range**.092067g**, sigma**.020957g**, window-fifths drift**−.016463g**.
- Mean error**−.180282g**; passes owner demo tolerance±.70g and retained
  stability checks. **10G_WINDOW_PASS=YES**.
- Display mean9.820010g, range9.788465–9.847820g; actual measurements retained.
- Commands: status twice only. No tare/reload/refit, NVS write, reset, flash or
  actuator command. Final status HEALTHY/valid, both actuator locks asserted.
- Verified loaded points so far:5g and10g in this session. Empty return after10g,
  20/35/38g, full transition timing and reboot stability remain unverified.

## 9. Empty return after10g — stable with retained negative bias

Evidence: `20261028T031527118850Z_observe_0g/`, completed `2026-10-28T03:16:03Z`.

- Owner confirmed10g removed/empty. Exact current-session RAM offset/slope/source
  remained unchanged. Only status was sent twice, no tare/reload/refit/reset/NVS write.
- After3s settling,30s window: **109/109valid signed triplets**.
- Signed mean**−.226914g**, min**−.270250g**, max**−.181002g**,
  range**.089248g**, sigma**.019641g**, window-fifths change**−.010065g**.
- Display stayed0.00g because the golden reference includes the additional
  display-only clamp for−.5g<mass<0g. Do **not** describe this whole window as
  falling within the±.20g deadband or use the display as proof of exact physical zero.
- The strict retained±.10g zero criterion is **not met** (`weight_window_pass=false`).
  Signed zero bias has changed from−.113516g after5g to−.226914g after10g;
  retain this inter-window trend. Each short window is stable, but overall zero
  stability is not established. No automatic offset correction was applied.
- This bias is small relative to the owner's±.70g mass-accuracy/coarse-intake
  objective, so continue the demo mass sequence with the bias explicitly recorded,
  without declaring strict zero PASS or diagnosing a mechanical cause.
- The legacy nonnegative control health is DEGRADED while diagnostic signed
  valid=true. Both actuator locks remain asserted and outputs0.

## 10.20g settled-window check — PASS

Evidence: `20261028T031718816708Z_observe_20g/`, completed `2026-10-28T03:17:55Z`.

- Owner declared20g placed. Same current-session receipt and exact RAM pair
  confirmed unchanged before/after capture: offset−671054.666666667counts,
  slope−1064.4473counts/g, sourceEXPLICIT_TARE_RAM_ONLY.
- Preserved3s settling data, then30s window: **109/109valid triplets**.
- Signed mean**19.682664g**, min**19.628340g**, max**19.735437g**,
  range**.107097g**, sigma**.022205g**, window-fifths drift**−.023665g**.
- Mean error**−.317336g**; passes owner demo tolerance±.70g and retained
  stability checks. **20G_WINDOW_PASS=YES**.
- Display mean19.683556g, range19.643225–19.707752g; actual readings retained.
- Commands: status twice only. No tare/reload/refit, NVS write, reset, flash or
  actuator command. Final status HEALTHY/valid, both actuator locks asserted.
- Verified loaded points in this session:5g,10g,20g. Empty return after20g,
  35/38g, full placement-response timing and reboot stability remain unverified.

## 11. Owner-declared empty after20g — inconsistent with observed load; STOP

Evidence: `20261028T031830474318Z_observe_0g/`, completed `2026-10-28T03:19:06Z`.

- Owner declared empty after20g, but initial signed mass19.604853g and the entire
  settled30s window remained near20g. Do not silently relabel the owner declaration
  or call this a successful zero return.
- **109/109valid triplets**; signed mean**19.622927g**, min**19.573851g**,
  max**19.667797g**, range**.093946g**, sigma**.019737g**,
  window-fifths change**−.017715g**. Display mean19.622921g.
- Median raw mean**−691942.238532counts**, compared with−692005.825688counts
  in the preceding20g window. New raw readings vary and device uptime advances;
  this is not merely a held display value awaiting a slow smoothing decay.
- Exact offset−671054.666666667/slope−1064.4473/sourceEXPLICIT_TARE_RAM_ONLY
  remained unchanged. Commands were status twice only. No tare/reload/refit,
  NVS write, reset, flash or actuator command. Final locks remain asserted.
- **EMPTY_RETURN_AFTER_20G: NOT_CONFIRMED / DECLARED_CONDITION_MISMATCH**.
  The capture's strict-zero result is false. Cause is not established: do not
  assert the owner forgot removal, that the scale is mechanically defective,
  or that an actual unloaded sensor failed solely from this inconsistent state.
- Preserve this capture and stop progression to35g pending confirmation of the
  physical load/empty condition. Never tare this approximately20g signal to0.

## 12. Reconfirmed empty after20g — near-zero signal observed, bias retained

Evidence: `20261028T032049485383Z_observe_0g/`, completed `2026-10-28T03:21:25Z`.

- Owner reconfirmed empty. This new window is consistent with an unloaded signal,
  unlike the previous approximately19.62g window. Cause of that earlier mismatch
  is not established; preserve both captures without attributing operator fault.
- Exact current-session offset/slope/source remained unchanged. After3s settling,
 30s window: **109/109valid signed triplets**.
- Signed mean**−.367203g**, min**−.439352g**, max**−.320980g**,
  range**.118372g**, sigma**.019519g**, window-fifths change**−.024828g**.
- Display0.00g throughout due to the golden display-only clamp for−.5g<mass<0g.
  Actual negative mass remains present in raw/signed evidence; it is not claimed
  to be within the±.20g deadband or an exact-zero measurement.
- Retained strict±.10g zero check remains **false**. Historical return means in
  this fixed-calibration session are−.113516g after5g,−.226914g after10g and now
  −.367203g after20g. The trend is recorded; no tare or offset correction applied.
- The signed bias is still below the owner's accepted.70g demo mass-error scale;
  proceed with the coarse-intake mass sequence while retaining zero-stability
  limitations. This is not a strict-zero/full-calibration PASS.
- Status twice only; no tare/reload/refit/NVS write/reset/flash/actuator command.
  Both actuator locks remain asserted. The declared-empty/approximately20g
  inconsistency is no longer present in this fresh window.

## 13.35g settled-window check — PASS

Evidence: `20261028T032243356311Z_observe_35g/`, completed `2026-10-28T03:23:19Z`.

- Owner declared35g placed. Current-session receipt and exact RAM pair confirmed
  unchanged before/after capture: offset−671054.666666667counts,
  slope−1064.4473counts/g, sourceEXPLICIT_TARE_RAM_ONLY.
- Preserved3s settling data, then30s window: **109/109valid triplets**.
- Signed mean**34.582390g**, min**34.518696g**, max**34.626736g**,
  range**.108040g**, sigma**.019302g**, window-fifths drift**−.000671g**.
- Mean error**−.417610g**; passes owner demo tolerance±.70g and retained
  stability checks. **35G_WINDOW_PASS=YES**.
- Display mean34.582442g, range34.544056–34.606850g. Do not replace measured
  mass with nominal35g; a future OLED meal-target label is separate from this reading.
- Commands: status twice only. No tare/reload/refit, NVS write, reset, flash or
  actuator command. Final status HEALTHY/valid, both actuator locks asserted.
- Verified loaded points in this session:5g,10g,20g,35g. Empty return after35g,
  38g/final empty, precise placement-response timing and reboot stability remain
  unverified. Existing recorded negative zero-bias trend remains unresolved.

## 14. Empty return after35g — stable window with continuing signed zero bias

Evidence: `20261028T032421620051Z_observe_0g/`, completed `2026-10-28T03:24:57Z`.

- Owner confirmed35g removed/empty. Exact current-session RAM pair/source
  confirmed unchanged; commands were status twice only.
- After3s settling,30s window: **109/109valid signed triplets**.
- Signed mean**−.455779g**, min**−.504174g**, max**−.404592g**,
  range**.099582g**, sigma**.022263g**, window-fifths change**−.023576g**.
- Display was predominantly0.00g, with a brief minimum**−.201670g** when signed
  mass crossed below the reference's−.5g small-negative clamp boundary. Display
  mean−.001850g; do not claim it stayed exactly0 throughout or enlarge the clamp.
- Strict±.10g zero check remains **false**. Fixed-calibration zero-return means
  now trend−.113516/−.226914/−.367203/−.455779g after5/10/20/35g. Short windows
  are stable but inter-window zero drift is present and retained in evidence.
- Mean signed bias remains smaller than the owner's.70g demo mass-error scale;
  continue to38g without tare/refit, retaining this limitation rather than claiming
  a strict-zero/full-calibration PASS.
- No tare/reload/refit/NVS write/reset/flash/actuator command; both locks asserted.

## 15. Owner closes physical sequence at35g — no38g test

Owner explicitly instructs: do not test38g; stop at35g. The empty observation
after35g has already been captured in section14. No additional serial command,
measurement, tare, calibration change, NVS write, reset or flash is needed or
performed to close this sequence.

### Scoped loaded-mass results (fixed post-restart RAM calibration)

| Owner-declared mass | Signed30s mean | Mean error | Valid triplets | Demo±.70g/stability |
|---|---:|---:|---:|---|
| 5g | 4.901414g | −.098586g | 109/109 | PASS |
| 10g | 9.819718g | −.180282g | 109/109 | PASS |
| 20g | 19.682664g | −.317336g | 109/109 | PASS |
| 35g | 34.582390g | −.417610g | 109/109 | PASS |
| 38g | NOT_TESTED | NOT_APPLICABLE | 0 | OMITTED_BY_OWNER |

- **LOADED_MASS_DEMO_5_10_20_35G_PASS: YES**, limited to the four observed
  settled windows and owner's declared test masses/demo tolerance.
- **TEST_SEQUENCE_STATE: CLOSED_AT_35G_BY_OWNER**. No pending38g placement.
- Final observed empty window: signed mean−.455779g, range−.504174..−.404592g,
  sigma.022263g. Display predominantly0.00g with brief−.201670g. The progressive
  negative zero bias remains recorded; **STRICT_ZERO_STABILITY_PASS: NO**.
- **FULL_PHYSICAL_CALIBRATION_PASS: NO / NOT_CLAIMED**. No38g result, exact
  placement-response timing, long-duration zero stability, persisted ESP32
  calibration activation or successful reboot-persistence verification is implied.
- Diagnostic RAM pair remains offset−671054.666666667counts,
  slope−1064.4473counts/g. There was exactly one initial tare in this explicitly
  verified post-restart session and no tare/refit between its weight windows.
  It is not a permanent production calibration authority and has not been saved.
- The earlier session, restart/calibration-loss observation, declared-empty20g
  mismatch and all raw/JSON/CSV/hash evidence remain preserved. No failed strict
  result was rewritten as PASS and no measurement was forced to its nominal mass.
- Servo/pump remained locked in the final observed telemetry. No actuator command
  was sent. Bounded capture scripts closed their serial handles on completion;
  no current continuous recorder is assumed active.

## Next owner action (current)

None required for this closed5–35g diagnostic sequence. Await a separate user
instruction before any further hardware testing, calibration activation,
persistence change, firmware integration, OLED/backend/frontend/AI work or flash.

## Cancelled38g placement instruction (superseded by owner stop)

Place the known38g mass and hold still; confirm placement for the next bounded
window using the same current-session receipt/pair. Do not tare. A final empty
window is still required after38g.

## Previous empty-return-after35g instruction (completed)

Remove35g, leave the scale empty and confirm removal. Record another zero-return
window with the same pair and no tare before placing38g.

## Previous35g placement instruction (completed)

Place the known35g mass and hold still; confirm placement. Record the next
bounded window using the same current-session receipt/pair without tare.

## Previous empty-condition confirmation request (resolved by fresh reading)

Ask the owner to verify the20g mass is fully off the weighing platform and no
other load/contact remains, while keeping the existing empty bowl/setup unchanged.
Confirm the actual state before a further bounded zero observation. Do not tare.

## Previous empty-return-after20g instruction (awaiting confirmation)

Remove20g, leave the scale empty and confirm removal. Record the next zero-return
window with the same pair and no tare before placing35g.

## Previous20g placement instruction (completed)

Place the known20g mass and hold still; confirm placement for the next bounded
window using the same current-session receipt/pair. Do not tare between weights.

## Previous empty-return-after10g instruction (completed)

Remove10g, leave the scale empty and confirm removal. Record another zero-return
window with the same pair and no tare before placing20g.

## Previous10g placement instruction (completed)

Place the known10g mass, hold still and confirm placement. Capture the same
bounded3s settling/30s window with the current-session receipt and unchanged
pair. Do not tare between this zero observation and10g.

## Previous empty-return instruction (completed)

Remove5g and leave the scale empty; confirm removal. Observe zero with the same
fixed RAM pair and **no tare** before progressing to10g. Do not place10g yet.

## Previous5g placement instruction (completed)

Place the known5g mass and keep it still. Confirm placement so a fresh bounded
window can be captured. Keep the USB–UART connected to the laptop without reset
or tare. No continuous recorder is assumed active after the earlier interruption.

## Earlier owner clarification (answered)

Confirm whether the bowl/fixture/load-cell position, any cable force/contact and HX711 power source are unchanged from the earlier passing zero window, or whether only the USB–UART connection was moved. Keep the scale empty and connected to the laptop while clarifying. No second tare or automatic reference reload is authorised/performed by this observation.

## Prior recovery instruction (completed by the empty window above)

Remove the5g mass and confirm the scale is truly empty. Preserve current coefficients/state and record a fresh raw-only empty window before deciding how to continue. **Do not automatically restore the old RAM pair or tare/refit to make5g match.** No repeat tare has been authorised or performed; the one-tare receipt remains in place. Servo/pump locks remain asserted in the fresh status.

## Earlier planned sequence (superseded by the blocker above)

Place a known **5g** mass gently; keep it still and report placement. Preserve all transition data and then evaluate a settled30s window with the same offset/slope. Return to empty and verify zero before the next mass. Do not reset/unplug or issue tare during the sequence: the diagnostic pair is RAM-only.

Passive continuous capture, when started by `record_physical.py`, sends **status only** and is bounded to20minutes. It records raw bytes/JSON across placements and stops if the RAM calibration changes, device uptime restarts, serial fails or its duration expires. It never loads a reference or tares automatically. The next3s settle/30s observation is analysed separately from the full preserved transition log.

Current recording started at `2026-10-27T18:20:20.839142Z`: `20261027T182020838399Z_continuous_reference/`, actual recorder PID21608, limit1200s. `ready.json` confirms the expected unchanged RAM pair, valid signed data and both actuator locks. `active_recording.json` points here (its STARTING state is a startup snapshot; consult ready/final summary and growing message log). **COM8 is owned by this recorder**: analyse `messages.jsonl`/raw files for subsequent weight windows; do not start another serial monitor or `physical_session.py weight` concurrently. `stop.request` in the capture folder requests clean stop; expiry also releases the port. Reconnecting after expiry must verify the same RAM pair, not re-tare automatically.

**HX711_FULL_PHYSICAL_CALIBRATION_PASS: NO — pending real mass sequence.**
