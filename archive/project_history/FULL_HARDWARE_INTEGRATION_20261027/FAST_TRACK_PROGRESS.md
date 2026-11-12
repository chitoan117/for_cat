# Fast-track physical progress — target nominal20cm

## Latest update: common target40cm and scheduler diagnosis

- HC1 remains PHYSICAL_PASS from reused20/40 evidence; no new HC1 capture.
- HC2 remains PHYSICAL_PASS,24/24 at nominal20cm.
- JSN2 now PHYSICAL_PASS at40cm:24/24 valid, median39.7194cm, stddev0.08848cm,
  zero timeout/stale reports or timeout-counter increase. Its20cm noisy result below remains historical evidence.
- Scheduler80ms at common40cm: HC1 24/24, JSN1 16/24, HC2 24/24, JSN2 23/24.
  JSN1 timeout reports8 and counter+9; scheduler is DIAGNOSED, not RUNTIME_PASS.
- Focused control at the SAME40cm: JSN1 single24/24 valid, median40.0795cm,
  stddev0.04506cm, counter+2 between reports. This supports a multi-channel/timing issue,
  not a proven acoustic cause or a failed JSN1 component. No extra HC1/HC2 retest was performed.
- Passive HX raw audit in parallel:24 samples,23 distinct,−666942…−666757, stddev48.55counts,
  no saturation; gramsnull/NOT_CALIBRATED. Reference mass UNKNOWN, load response NOT_TESTED.
- A small sensor-only guard release is SOFTWARE_READY and UNFLASHED under
  `guard_tuning_release/` in the same milestone. RAM-only guard supports EXACTLY60/80/100ms,
  default80; invalid values/busy updates rejected. No NVS, threshold, actuator, RTC or pin change.
  Current production firmware is still fixed80 until operator flash. No backend/Flutter/AI change.
- Both MCU build profiles succeeded; focused UBSan scheduler183 assertions, real setup/loop34,
  legacy drivers3351, and2 frames accepted by the existing bridge. No physical guard60/100 result yet.
- One shared harness now has bounded `--sensor all --guard-sweep --samples 24 --target-cm 40`;
  it tests60/80/100 once each, keeps all attempts, and selects the smallest TESTED window passing.
  If none qualifies it stops; no automatic flash or endless tuning. No full suite re-run for the small harness patch.

**ACTION REQUIRED: manual app-only flash of the guard release, with external servo/pump power isolated.
Keep the common target at40cm. Then run the bounded sweep without repeating single-channel proofs.**

The table below is the earlier nominal20cm checkpoint, retained for chronology.

One tool: `observe_ultrasonic.py`; fixed select-only command whitelist, one serial owner,
JSON/CSV/statistics/identity/safety and SHA256. Production bridge/firmware/AI unchanged.
Evidence remains in the existing milestone, subdirectory `fast_track_ultrasonic/`.

| Sensor | Result | Real evidence |
|---|---|---|
| HC1 | PHYSICAL_PASS | Reused24/24 valid at20cm, median21.4203; mean21.33675 vs38.74471 at prior40cm. No repeat capture. Scope basic ranging20–40, not accuracy/soak certification. |
| JSN1 | PHYSICAL_PASS |24/24 sampled reports valid, median24.1815, stddev0.1260cm, spread0.4802cm. Cumulative acquisition timeout counter increased2 between reports; report-valid rate is not an all-acquisition success claim. |
| HC2 | PHYSICAL_PASS |24/24 valid, median21.9863, stddev0.0724cm, no timeout report, no cross-channel overwrite. |
| JSN2 | DIAGNOSED |20/24 valid,4 timeout reports, median23.7871, max84.6181, stddev13.2597, max jump60.8653cm. Must not pass on the median alone. |

JSN2 near-range/reflection limitation is suspected at nominal20cm, not proven; alignment/wiring/echo timing remain possible causes.
Single-channel mode had the other3 channels disabled. Do not call this observed JSN2 instability cross-talk from the scheduler.
Next required action is move the common flat target to about40cm, covering the JSN2 beam, then run only JSN2 again.
If stable, run the four-channel sequential scheduler without repeating the3 accepted single-channel tests.

Current firmware exposes80ms guard only. It has no runtime60/100ms setting command;
if guard tuning is actually needed, record that manual flash/review is required rather than pretend a setting was changed.

Harness issue corrected: the initial new receive loop read bytes but omitted appending non-newline bytes.
Those `NO_SAFE_BASELINE_FRAMES` attempts are harness failures, not sensor measurements. A bounded LineBuffer now
has split-JSON/CRLF/overflow recovery tests. The POSIX adapter preserves control lines, tests synthetic PTY roundtrip,
and records actual I/O traces.11 focused harness tests on Linux,17 backend schema tests and9 Flutter mapping tests passed;
no repeated full-suite regression while hardware collection proceeds.

Scheduler physical/cross-talk is NOT_TESTED until JSN2 is resolved. HX711 raw/calibration waits behind that gate.
Servo/pump/AUTO remain blocked/disarmed/output0; no actuator/flash/NVS command sent by this harness.
