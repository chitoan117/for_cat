# FOR_CAT timed servo closure — 2026-11-03

Owner requested operation without the GPIO47 limit switch.

The candidate disables GPIO47 setup, polling and motor decisions. Normal and diagnostic close operations run for `close_ms`, then stop PWM. Diagnostic opening uses `open_ms`. STOP remains available. A close after an HX failure remains a fault requiring inspection.

Defaults inherited from the existing source: opening 550 ms at 1300 us; closing 4000 ms at 1700 us; neutral 1500 us. **The closing duration has not been measured on the new mechanism.** Timing commands accept 100–5000 ms only while idle. Timing changes are RAM-only and revert to source defaults after restart.

Telemetry reports `closure_mode=TIMED`, `limit_switch_enabled=false`, and null limit/physical-position fields. Elapsed time does not establish physical closure or measured dispensed mass.

Artifacts:

- `esp32.original.ino`: byte-for-byte source backup.
- `esp32/esp32.ino`: candidate firmware.
- `change.diff`: reviewed source delta.
- `test_timed_close.py`: host harness extracting the actual modified control functions and branches, with fake GPIO/PWM.
- `native_test_result.txt`: checks for timer boundaries, GPIO47 isolation, HX-failure close, millis rollover, STOP, diagnostic duration and timing input bounds.
- `output/`: Arduino CLI build artifacts, when compilation completes.

No hardware movement or firmware upload was performed for this change. Sensor electrical behavior, servo stop behavior and mechanically correct timing require physical validation.
