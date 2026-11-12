# Python simulator ↔ ESP32 portable-policy parity (RC1)

Historical navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL RC1/RC2 checkpoint — NOT CURRENT counts or implementation inventory.** Policy comparisons remain useful; read `CURRENT_PROJECT_STATE.md` / `PRE_HARDWARE_FINAL_BASELINE.md` for the handoff baseline. Synthetic desired outputs are not real actuator evidence.

**RC2 delta:** `command_dispatch.h` is now used by SIM firmware to execute the portable feeding policy with explicitly synthetic sensors, while HW_SAFE alone continues to ACK then reject every feed. Both recheck sensors before desired-open and pump health while filling. NVS now uses a CRC-protected 25-byte versioned storage envelope (`daily-v3`), not raw struct bytes; no real NVS operation validated. UART v1 result bytes remain unchanged. The RC1 comparison below is retained as the original policy checkpoint; `PRE_HARDWARE_RC2.md` and `RC2_ORCHESTRATION_AND_HISTORY.md` describe current dispatch/history.

Compared: `jetson/app/simulator/controller.py` and `esp32/include/safety_logic.h`. The host C++ harness executes policy assertions; Python scenarios separately execute the simulation. Both are **software logic**, not real sensor/actuator tests. UART v1 has not changed.

| Rule | Python simulator | C++ safety policy | Assessment |
| --- | --- | --- | --- |
| Target portion | 1–50 g | 1–50 g | Match |
| Daily portions | maximum 4 | maximum 4 | Match |
| Daily grams | maximum 150 g | maximum 150 g | Match; over-limit measured completion faults |
| Cooldown | 3600 s, clock rollback rejected | 3600 s, clock rollback rejected | Match |
| RTC invalid / older day | reject/hold SAFE_BOOT | reject/hold SAFE_BOOT | Match |
| Food empty | reject before opening; fault if lost during dispensing | same | Match |
| HX711/weight fault | reject on invalid/nonfinite/negative reading; fault during dispensing or closing | same | Match in outcome; diagnostic reason wording differs |
| Servo fault | reject precheck; fault during closing | same | Match |
| No weight progress | 0.2 g within 5 s | 0.2 g within 5000 ms | Match conceptually |
| Feed timeout | 20 s including closing | 20,000 ms including closing | Match conceptually |
| Safe boot / reboot | servo flag OFF; an interrupted `needs_inspection` record locks out future requests | desired-open flag OFF; persisted inspection flag locks SAFE_BOOT | Match in fail-closed policy |
| Water low / recovered | low <25% for 3 samples; off at ≥75% | same | Match; hysteresis/filter |
| Water sensor or pump fault | OFF; sensor fault recovers after 3 valid readings, pump fault latches | same | Match |
| Water no progress | <2 percentage points within 5 s faults OFF | same in 5000 ms | Match conceptually |
| Pump maximum runtime | 30 s faults OFF | 30,000 ms faults OFF | Match conceptually |
| Water safe boot | simulated pump OFF | desired pump OFF | Match |

**Deliberate differences and limits:**

- Python uses monotonic floating seconds and a memory/file `SimulationSafetyStore` (revision 1); C++ uses unsigned 32-bit `millis()` subtraction, RTC epoch seconds, and revision-2 `NvsSafetyStore`. Python's optional simulation store is not flash/NVS. C++ requires a successful write-ahead NVS save before setting its desired servo-open flag and saves completed counters before COMPLETE; neither NVS endurance nor timing has been hardware tested.
- Python simulated sensors/pump default explicitly healthy **inside the digital twin**. C++ real-driver contracts default NOT_VALIDATED and all GPIO pins remain unassigned. No simulated health can turn on real outputs; `ACTUATOR_OUTPUTS_ENABLED=0` is a hard compile-time guard.
- Python uses text reason `SENSOR_FAULT`, `HX711_FAILURE`, `FEED_TIMEOUT`; C++ uses enum reasons such as `INVALID_WEIGHT`, `HX711_FAULT`, `TIMEOUT`. Both map execution failures to ERROR and precheck failures to REJECTED conceptually; v1 FEED_STATUS carries only PENDING/SUCCESS/REJECTED/ERROR, not a wire reason code.
- At RC1 the firmware ACKed then rejected all feeds. At RC2 this remains true for HW_SAFE; SIM additionally executes synthetic policy and reports authoritative simulated final results. The portable C++ policy is **not** connected to physical actuators or a v1 target-grams payload. Real water telemetry is absent in UART v1.
- Python `SimulationSafetyStore` is explicitly exercised in reboot tests. The native C++ harness uses a `TestStore` to exercise restoration and write failure but does not exercise ESP32 Preferences on a device. Date/RTC, sensor scaling and tick wrap must still be tested on physical hardware before any output could be enabled.
