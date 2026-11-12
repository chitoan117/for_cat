# FOR_CAT pre-class readiness audit — 2026-11-04

Owner requested checking Jetson, offline use, and flashing ESP32 while the sensors are disconnected. All physical movement tests remain pending assembly. No servo-open/close, fine-adjust, feed, pump or buzzer-test command was sent during this audit.

## Firmware

Updated source: `D:\CODE_TEST_LOADCELL_CHUAN\esp32\esp32.ino`.
Source SHA256: `0d1280c9bbc6f25c638a5dc9d4f8514c32d876b5b09a10e4bf7e26d77323164d`.
App SHA256: `f0e91dcb650f96e9f494d011c493888211b9658e24a686898693c892ac273c79`.

The HX711 driver, conversion, median/filter and NVS calibration routines are byte-for-byte unchanged from the previous source (text-normalized comparison). Servo remains GPIO6: right/open 1400us for1100ms, left/close 1600us for900ms, neutral1500us, fine170ms. GPIO47 remains disabled. Existing close trigger30g / upper40g constants were retained; 35g actual dispensed mass is not established by software checks.

Correctness fixes:

- Manual button/Web feed now requires a fresh calibrated measurement; stale weight or invented zero cannot initiate the feed.
- Early/timed manual close below the target and a measured >40g close do not become `MASS OK`.
- Recovery closing is allowed its bounded900ms even after the global wait deadline.
- Invalid HC1 observations break the consecutive approach sequence; duplicate frames do not count.
- Read-only `hx_diag` exposes rejected raw values and GPIO levels for wiring diagnosis.

Arduino ESP32-S3 compile PASS (392973 program bytes;33680 globals). Native tests extract the actual modified output/servo/control branches and run against fake I/O. Tests cover pulse/timing, neutral hold, STOP, millis rollover, missing/stale loadcell, threshold/overshoot/timeout/HX-loss, HC1 consecutive readings and recovery timeout. See `native_test_result.txt` and `firmware.diff`.

Flash: backed up actual0..0x150000, verified matching partition table and OTA selection, wrote app0 only, esptool verify PASS. NVS before/after byte-identical. New image booted and read-only diagnostics returned. Bridge restored and normal state-machine start resumed; data updates were observed across five consecutive samples. Sensor FAULT/INITIALIZING/null readings are expected with disconnected wiring and are not a physical sensor pass.

## Jetson and web

- Linger=yes; AI/API/bridge enabled and running. API localhost HTTP200.
- AI supervisor waits when camera is absent; it does not prove recognition is working. `/dev/video0` was absent. Existing engine is present (8696694bytes), SHA256 `48fe40017461d2e4edab33c47b30194b84ba7714e32e6d3d2aa4649f5b7471fb`.
- Tailscale Serve route persists. No new4G test was performed in this audit (previous owner confirmation remains historical evidence).
- Offline browser test PASSED: actual Flutter dashboard and WebSocket rendered at127.0.0.1 with all page requests restricted to loopback; no external assets or write requests were attempted. See `offline_web_result.json` and `offline_page.png`.
- Ethernet/SSH was not disconnected and a full power-off/no-network physical test was not performed. The owner will do that at school.
- Touch panel and Desktop/cat launchers still point to the correct same backend; explicit Offline opens127.0.0.1.
- Time zoneAsia/Ho_Chi_Minh, current time/RTC synchronized. No battery-retention/offline cold-clock guarantee was tested.

Bridge metadata fixes were tested with4 temporary-SQLite cases: calibration status comes from firmware; no physical-closed observation means servo positionUNKNOWN. Dispatch/control methods are AST-identical; no inference/feeding/network policy logic was changed. See `bridge_metadata_result.json`.

## One administrator step pending at latest inspection

ModemManager logs show it probes ttyACM0 as a Generic modem at enumeration, matching the startup serial interference. A rule restricted to VID1a86/PID55d3/serial5C85066678 is staged. The remote sudo command was rejected by the OS because a password is required; this was not an automatic approval-review rejection. The ignore rule had not yet been installed at the latest inspection.

The owner needs to run on Jetson/MobaXterm:

```sh
sudo /usr/bin/python3 /home/toan/for_cat/evidence/readiness_20261104/install_usb_rule.py
```

This installs only the device-specific ignore rule, backs up a differing existing rule, and reloads udev. It does not disable ModemManager globally or alter modem/Wi-Fi settings. After re-enumeration/reboot, verify the ignore properties and fresh serial telemetry. Current serial samples update, but persistent protection against future startup probing remains pending this administrator step.

## Assembly acceptance remaining

Wire/inspect with power off, then power on. Check valid raw/grams and existing calibration, all4ultrasonic inputs, camera and AI, OLED/button, servo direction/timing/stop on the actual assembly, and actual dispensed mass. In absent data states no physical success is claimed. No pump automatic-control feature was added. Restore/backup and logs are under `/home/toan/for_cat/evidence/readiness_20261104` and this local audit folder.
