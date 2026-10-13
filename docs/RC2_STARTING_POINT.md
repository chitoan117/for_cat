# RC2 starting point (before source changes)

Historical navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL / NOT CURRENT:** starting-state audit only. Current handoff is `PRE_HARDWARE_HANDOFF.md`; current architecture/status is `REFERENCE_ARCHITECTURE.md` / `CURRENT_PROJECT_STATE.md`.

Milestone M2. RC1 evidence/document retained: `PRE_HARDWARE_RC1.md` and the original progress checklist in `PROJECT_STATUS_CURRENT.md`. Workspace is not a Git repository (`git status --short` returned "not a git repository"); no reset/commit/push is performed.

Initial `scripts/run_checks.ps1` rerun: 99 Python tests passed; native C++ 101 assertions passed; 7 UART v1 vectors match; 21 simulator definitions covered. `esp32dev_sim` and `esp32dev_hw_safe` PASS, each RAM 22,692/327,680 bytes and flash 284,076/1,310,720 bytes. Profiles target classic `esp32dev`, Arduino, pinned `espressif32@55.3.311`, actuator outputs 0. UART CSV and API v1 remain frozen.

No Jetson/Logitech/ESP32/S3/sensor/actuator validation. Real dataset absent and AI untrained. Historical PC camera result is not repeated in RC2.

## S3 configuration sources inspected locally
- Platform `boards/esp32-s3-devkitc-1.json`: official DevKitC-1 **N8, 8 MB QD, no PSRAM** default. This is a compile surrogate, never the unidentified 44-pin seller board.
- Arduino package `boards.txt`: `esp32s3.menu.FlashSize.16M.build.flash_size=16MB`; `esp32s3.menu.PSRAM.opi.build.psram_type=opi` and `-DBOARD_HAS_PSRAM`.
- Platform builder `_get_board_memory_type`: honors `build.arduino.memory_type`/`build.psram_type`; installed S3 libraries include `qio_opi/`.
- Package partition `default_16MB.csv`: 0x640000 OTA app slots; ends at 0x1000000 (16 MiB).
- Existing packaged `freenove_esp32_s3_wroom.json` demonstrates `qio_opi`/`opi` with `BOARD_HAS_PSRAM` for an R8 configuration, but is not used as the seller pinout.

These prove compile support for a 16 MB flash / OPI-PSRAM surrogate configuration. Actual 16 MB flash, 8 MB PSRAM detection, USB implementation, antenna/module and all seller GPIOs require physical identification. Compile result cannot prove memory capacity at runtime.
