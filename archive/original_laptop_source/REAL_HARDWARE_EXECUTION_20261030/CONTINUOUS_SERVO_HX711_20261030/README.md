# MG996R continuous + HX711 — source-only fork

**PASS_OFFLINE21 new cases**, `tests_sensor_edges_fixed/result.json` / `compile.log` / per-case logs. No APP image built, flash, Serial or load activation. Old position-based images/source remain unchanged, but **must not be used as CLOSE/OPEN position control for the newly assumed continuous servo**. Actual servo type still requires verification.

## Exact changes

-`include/continuous_servo.h`: raw PWM adapter, calibrated neutral/deadband and opposite open/close **rotation** pulses. Existing50Hz GPIO6 LEDC driver is unchanged. No angle conversion or default neutral1500. Unknown/unverified calibration fails configuration. Electrical1–2ms/initial span≤100us retained, not widened.
-`include/continuous_dispense.h`: new continuous-motion FSM; ARM does not move. Reserve/persist request ID before rotation; four distinct fresh baseline samples. Bounded opening, then neutral while HX continuously measures; new measurement reaches `35-closing_lead_g` → bounded close rotation → neutral hold → settle/four qualified stable readings. Final mass is measured delta, never opening-time estimation or coerced35g. No reopening/top-up after closing.
-Lead defaults0g; positive lead≤3g requires actual lead calibration. Acceptance30–40g is not the cutoff: even maximum configured lead starts close no earlier than32g. Lead/times include actual flow, HX filter latency, closing travel/inertia; fixture2g is not a live preset.
-Missing position feedback: only explicitly approved supervised mode; timed opening/closing never sets position proof. In-band final produces `MEASURED_NEEDS_OWNER_CONFIRMATION`, keeps journal pending/inspection-required, **not COMPLETE**. Automatic mode requires healthy/qualified fresh OPEN/CLOSED feedback and final CLOSED after close began, plus weight/calibration/journal checks. No GPIO or provider is invented.
-Faults stop further opening. Default fault action/STOP is neutral and latched FAULT; **neutral does not close the gate or stop gravity food flow**. One bounded fault-close is optional, supervised-only and explicitly configured after direction/timing review; never upgrades closure or resets an existing close deadline. STOP never starts a reverse/close move. External load cutoff/food-isolation response remains necessary.
-Neutral is a stop command, not physical stop proof. Keep neutral PWM by default; detach after it only when signal-loss stopping behavior was separately verified. Timeouts cover motion, total transaction, baseline/settling and1500ms heartbeat lease. Duplicate IDs/pending reboot and reentrant late callbacks cannot reopen/resurrect COMPLETE.
-`include/continuous_hx_adapter.h`: read-only mapping of existing `hx.grams` control reading, NOT display deadband/smoothing; exact local calibration-change generation. No tare/refit/save. All31 copied headers, including `m4/hx711.h`, remain byte-identical.

This library is **not bound to the old positional feed-link payload/state machine or an APP main yet**. Do not map its supervised result to old SUCCESS. Live binding/APP build follows the real neutral/type/timing/position-evidence review; no production, AI, Web or outbox framework changes here.

## Next physical step — only after owner approves the bench

1. Cut only servo load power; keep ESP32/Jetson/USB powered to preserve RAM. Decouple the gate so the shaft can move freely, mark shaft; pump motor wires remain isolated. Use a reviewed PWM tester/instrument, never two signal sources on GPIO6. No old automatic CLOSE/OPEN sequence.
2. Confirm continuous behavior and find actual neutral/deadband with short bounded trials/cutoff ready. Record pulse, movement/drift/video; do not declare1500us neutral by name. Verify stopping and, separately, signal-loss behavior before permitting PWM detach.
3. Identify the two rotation directions and safe opening/closing time limits on the real mechanism. No full-range sweep or guessed angle. Then measure real closing lead/inertia using trusted HX readings under supervision. Current fork has no numeric live presets or hardware approval.

Without reliable gate-position feedback the first dose remains supervised/unconfirmed, even if final mass is38g. Automatic completion still needs a qualified position source/criterion; time/PWM is not that source. Existing flash/bank/security/ECHO/calibration-preservation gates still apply before any later board operation.
