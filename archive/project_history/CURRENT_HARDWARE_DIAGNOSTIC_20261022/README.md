# Current wired hardware diagnostic — software prepared, PHYSICAL NOT VERIFIED

User reports main components physically WIRED; food/water reservoir sensors #2
are NOT WIRED, not faulty. Start with **`CURRENT_HARDWARE_DIAGNOSTIC.md`**:
ordered sensor-only boot/OLED/DS1302/PIR/HX711/approach/water steps, then *separate*
servo and pump bench profiles. Sensor image `diag_current_hardware` never drives
GPIO6 servo or GPIO7 pump. No unattended feed/refill, CAT/Jetson detector unchanged.

Pump F5305S IN polarity and boot/reset OFF bias have NOT been physically verified;
`diag_pump_bench` is inert and cannot touch GPIO7. Active high/low firmware can
compile but must NOT be selected/flashed based on a guess. No active pump image
is preselected as the physical one for this handoff.

`deploy/` contains bootloader/partition/app/factory products with hashes for the
safe SENSOR-ONLY profile. **Factory flash can overwrite NVS calibration.** If the
board is already provisioned, verify actual installed bootloader/partition data
and use only the app image at0x10000; if mismatched, stop and review/backup before
any deliberately authorized factory flash. Physical board pinout/polarity/behavior
cannot be inferred from compile or USB status alone.
The generic deploy manifest says `flash_image=firmware.factory.bin` for a fresh
first installation; **that is not a recommended action after HX711 calibration**.

`host_checks/` provides fake-IO firmware-loop/Jetson-parser tests and build logs;
these are not physical PASS. For each actual block send serialRXlog, typed
commands, photos/video and real measurements, including power/brownout events.
