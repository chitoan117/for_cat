# Servo GPIO6 — correct existing firmware/commands, physical test still gated

Updated after OWNER confirms BOTH pump motor wires removed from F5305S OUTPUT. Supply5V–10A, GPIO7/GND unchanged: **pump load isolation OWNER_CONFIRMED**, no repeat requested. OFF polarity does not block this servo-first route. Motor wires stay removed/insulated throughout flash/servo testing.

## Existing image remains unchanged

`..\INTEGRATED_MANUAL_CANDIDATE\build_safe_txatomic\artifacts\firmware.bin`

-415456bytes, SHA256 `77faf09775e55731b08c511ac852273b9839963c081ebe924035f8f9aecaac93`.
-Build/30 existing integration regressions carried forward; no firmware rebuild or old regression rerun.
-Source checked: `firmware/include/m4/servo_bench.h`, `manual_station_policy.h`, `src/manual_station.cpp`, `manual_console.py` in the locked candidate.
-Boot DISARMED/PWMoff/configuration empty; no CAT/DOG/button/reconnect action. Configure once/boot,1000–2000us electrical bounds, span≤100us, max3arms/moves per boot; arm2s, move250ms, close350ms, hard deadline3s. These are software limits, not mechanical verification.
-ARM attaches PWM at CLOSE and can move immediately. OPEN moves once, automatically returns to CLOSE after250ms, then PWMoff/DISARMED after350ms. Explicit close/disarm also return to the configured reference; no physical closure feedback exists.
-`stop`/`servo stop` latches fault/PWMoff. Console STOP and exit/QUIT send that global STOP. Do not auto-reset/re-arm to clear it.

## Outstanding gate before any activation

Actual servo model/rated voltage, servo V+/GND/signal wiring, external load cutoff and safe unloaded mechanism; reviewed initial pulse values; actual candidate flash/boot verification after bank/security/ECHO/calibration/recovery gates. Shared5V–10A rating alone does not prove these. Full OPEN/CLOSED pulses are NOT_MEASURED. If full gate travel requires >100us, this image cannot perform that full travel; do not widen or invent values before physical findings/review.

## Only after approved maintenance, image verification and separate movement approval

On Jetson, set `C` to the NEW staging directory actually transferred/verified; do not assume it already exists. Console never stops services; original Bridge must already have released Serial under that approved window. `APPROVAL.json` must contain the exact reviewed image SHA, expiry/approver, `allow_servo=true`, servo power/mechanics review, pump-load isolation and reviewed four pulse values; pump/buzzer permission false. Existing manual_console CLI:

```bash
python3 -B "$C/manual_console.py" --execute OWNER_APPROVED_STATION_CONSOLE --approval "$C/APPROVAL.json" --image "$C/firmware.bin" --out "$C/servo_trial_$(date -u +%Y%m%dT%H%M%SZ)" --seconds 120
```

**Not authorized to run now.** In that human console, only after actual approval/values are known:

```text
SESSION
SEND servo status
SEND servo configure MIN_US MAX_US CLOSED_US OPEN_US CONFIRM
```

MIN/MAX/CLOSED/OPEN are placeholders, NOT guessed1500/1550 or angles. First get the intended small interval reviewed against actual servo/mechanics. Once configured and the owner explicitly approves the first movement:

```text
SEND servo arm YES
SEND servo open
```

OPEN must reach MCU within the2s arm window. One explicit cycle: configured CLOSE → OPEN → automatic CLOSE → PWMoff. Do not immediately append `servo close` if observing the bounded250ms open interval. After ≥600ms, `SEND servo status` should record DISARMED/pulse0; confirm white gate physically covers the outlet. `SEND servo close` is supported while ARMED/MOVING; after automatic DISARMED it normally rejects NOT_ARMED, so do not re-arm merely to obtain a prettier ACK.

Console logs JSON status instead of printing every frame. A separate terminal may read `events.jsonl`/`serial_raw.bin`; it must not open the tty. Save approved pulse values, timestamp/raw log and video of real travel, return, no binding, no supply reset. ACK=ACCEPTED is not physical PASS or FEED_STATUS COMPLETE.

Emergency: human `STOP`, plus physically cut servo load power if jam/abnormal motion/no response. PWMoff does not guarantee mechanical close or zero motor current. Keep fault/evidence; no automatic retry. Do not run food or a35g trial in this bench.

**Immediate next owner step:** provide servo model/label and one wiring photo showing servo V+ from the5V supply, servo GND referenced to ESP32, GPIO6 signal and the independent servo-load cutoff. Do not power/move/reset/unplug ESP32 to produce this evidence. Pump isolation is already accepted.
