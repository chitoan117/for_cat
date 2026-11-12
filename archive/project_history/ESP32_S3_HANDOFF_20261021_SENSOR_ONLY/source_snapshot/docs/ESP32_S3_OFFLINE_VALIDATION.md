# ESP32-S3 V2: actual firmware-loop OFFLINE validation

**No ESP32 or sensor connection is required for these tests.** They do not open a
serial device, drive actual GPIO, flash a board or train a model. Use the V2 bundle
`D:\for_cat\ESP32_S3_HANDOFF_20261018_V2`; the earlier20261017 bundle is historical.

## What runs

`esp32/test/firmware_loop.cpp` includes the **actual**
`esp32/src/diagnostics.cpp` with the explicit safe single-station profile. Its real
`setup()` and `loop()` run in fresh host processes for every named case. Only the
Arduino boundary (GPIO, clock, Serial, Wire and Preferences) is replaced by small
adapters under `esp32/test/arduino_stub/`. These are test include paths ONLY;
PlatformIO firmware compilation never includes or uploads them.

The existing DS1302 pin emulator was moved unchanged into
`esp32/test/ds1302_fake_pins.h` and shared with the original driver regression.
No second RTC implementation/driver was added. ADC bit inputs and ultrasonic
echoes are explicitly generated test data; fake NVS is an in-memory map.

Actual firmware JSON passes through the real Jetson function
`bringup.sensor_monitor.parse_report`. Each run saves serial transcripts,
decoded JSONL and a summary with `scope=SYNTHETIC_FIRMWARE_LOOP`,
`physical_hardware_used=false`, `flashed=false`. The receiver validates the same
disabled-output/null/finite-number contract it would require from a real board.
These reports must never be imported as real sensor history.

This is **not** instruction-accurate S3/FreeRTOS simulation, electrical validation,
measured pulse timing, sensor accuracy, RTC retention or OLED-panel validation.
Driver busy states are checked to prohibit slow IO during echo acquisition; actual
hardware/RTOS timing still needs a separate physical test.

## Real defect found and fixed

Before V2, successful `scale.tare()` and `scale.calibrate()` updated the scale
driver but not the shared in-memory `calibration.hx711` record. In combined mode,
`food-geometry` / `water-geometry` call `copyCalibration()`, which reapplies that
record. This could erase an unsaved new factor, or revive an older pre-tare factor.

The new `calibration_flow` test failed on that path before the correction. Fix:
after successful tare/reference calibration, immediately synchronize
`calibration.hx711 = scale.calibration`. Tare therefore also propagates its invalid
factor state. Explicit NVS load still intentionally replaces state; persistence
still requires `save YES`. No boot tare/save, schema change, actuator permission
or UART v1 change was introduced.

## Six named cases

| Case | Checked workflow |
| --- | --- |
| boot_missing | No connected sensors; null values; no startup ECHO/buzzer GPIO; no RTC register/NVS writes |
| calibration_flow | Raw -> tare -> reference -> grams; independent level geometry preserves factor; explicit save/load; NVS failure; timeout nulls; ADC recovery; new tare cannot revive an old factor |
| independent_echoes | FOOD acknowledgment does not enable WATER; both channels get measured synthetic distances/percent; no overlapping pulses or slow IO during acquisition |
| faults_and_recovery | Missing/stuck WATER echo does not stop FOOD/RTC; invalidates water values; ADC timeout clears grams; water recovers; OLED failure does not block sensors |
| clock_and_parser | CH invalidates clock; unsupported century rejected; explicit set/readback/WP restore; oversized/binary/malformed/actuator commands recover safely; no charger writes |
| button_and_buzzer | Short release produces one rejected feed intent; long hold does not; buzzer untouched before explicit driver acknowledgment and stops after its bounded pattern |

Each case additionally checks zero GPIO14/15 touches, balanced HX711 critical
sections and DS1302 turnaround without contention. Simulated loop iterations are
not counted as extra tests/assertions or physical stress.

## Exact standalone commands

From `/home/toan/for_cat` on Jetson, or a complete host checkout with g++:

```sh
BUILD=$(mktemp -d /tmp/esp32-loop-offline.XXXXXX)
g++ -std=c++17 -O1 -g -Wall -Wextra -Wpedantic -Wshadow -Werror \
  -Wno-unused-variable -Iesp32/test/arduino_stub -Iesp32/include \
  esp32/test/firmware_loop.cpp -o "$BUILD/firmware_loop"
python3 -B scripts/test_firmware_loop.py --binary "$BUILD/firmware_loop" \
  --output "$BUILD/results"
```

`-Wno-unused-variable` permits legacy mode-specific globals in the included
production file. Original strict driver tests still run separately. No global
warning policy or actual MCU target was weakened. Fixture files are not compiled
with new permissive production pin/output settings.

ASan/UBSan/leak-detection variant:

```sh
g++ -std=c++17 -O1 -g -Wall -Wextra -Wpedantic -Wshadow -Werror \
  -Wno-unused-variable -fno-omit-frame-pointer -fsanitize=address,undefined \
  -Iesp32/test/arduino_stub -Iesp32/include esp32/test/firmware_loop.cpp \
  -o "$BUILD/firmware_loop_asan"
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
  python3 -B scripts/test_firmware_loop.py --binary "$BUILD/firmware_loop_asan" \
  --output "$BUILD/results_asan"
```

Output directories must be NEW. The existing full release checker now compiles
and runs this matrix automatically, with a new timestamped evidence directory on
each invocation, preserving normal repeatable-check behavior:

```powershell
.\scripts\run_checks.ps1
```

## Results actually executed

| Layer | Result / exact scope |
| --- | --- |
| Full Python suite |365 PASS,0 failed/skipped/errors |
| Existing native safety |140 checks PASS;7 UART v1 vectors match |
| Existing driver regression |3351 assertions PASS (count unchanged by emulator extraction) |
| New real-loop cases |6 named cases,131 C++ assertions PASS |
| Firmware -> actual Jetson parser |21 diagnostic reports decoded/validated across those6 cases |
| Compile guards |34/34 PASS |
| Safe PlatformIO profiles |19/19 build PASS |
| Nano ASan/UBSan + LSan |All6 cases and existing native safety/driver suites PASS, no reports |
| Physical board / live serial / motion |NOT USED / NOT TESTED |

Host release evidence:
`C:\Users\chito\AppData\Local\Temp\opencode\for_cat_esp32_checks_v2_20261018`.
Target sanitizer/evidence directory:
`/home/toan/for_cat/evidence/esp32_firmware_loop_v2.y29YQe/`.
The six cases are reported separately from the365 Python tests. Decoded reports
are messages, not additional test cases. Python receiver-check assertions are not
given a fabricated separate count. TSan is not claimed for the single-owner loop
or vendor RTOS; no concurrent shared-instance guarantee is added.

## Current artifacts / deployment

V2 app:394512B, SHA256
`dd23d70c42e8d8f6665bf57a2bb7eca8d7337d10e11089e4c0164d997b8bca1b`.
V2 factory:460048B, SHA256
`2aebdfd404c54e90bf84a242f6070b5097f226ce65109bfa35d2fef0917cacfb`.
Use matching V2 manifests, not hashes from the earlier image. Old bundles/logs
are retained for provenance and marked superseded, not overwritten/deleted.

Normal UART v1 implementation, safety policy, disabled actuator pins/flags and
validated CAT/DOG source/binary/engine are unchanged. No new Git commit/push or
MCU upload was performed. See `ESP32_S3_SENSOR_STATION.md` for wiring/calibration
and the explicit future hardware procedure; real hardware remains a separate gate.
