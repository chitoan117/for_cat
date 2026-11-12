# Timestamp and clock policy

- Python API, SQLite typed records and event history store timezone-aware UTC timestamps. A missing actual capture time stays `null` in dataset metadata; source video relative offsets are stored separately and must not be misreported as real wall-clock capture times. Replay frame timestamps are relative to replay start, **not** original camera capture time.
- Elapsed behavior sessions, feed/water timeouts, serial read deadlines and cooldown within a live process use monotonic clocks/ticks. Do not compute safety timeouts from potentially adjusted wall clock. ESP32 unsigned millisecond subtraction handles tick wrap; actual hardware rollover remains untested.
- Jetson dateshistory/REST; currentESP32RTCisDS1302withUTC2000–2099convention,3-wire16/17/18. Genericvalidday/epoch/dailylimits/cooldownstillauthoritativeonMCU; requestsneveroverrideit. Invalid/halted/rollbacktimeorcorruptNVSdeniesfeed; noresetresume. EarlierplannedDS3231selectionishistory.
- SyntheticPCtimecannotvalidateDS1302crystaldrift/battery/retention/synchronization orNVSdurability. RecordactualUTCreference/conditions/errors; timestampdomainnotauto-initializedfrombuildtime.
