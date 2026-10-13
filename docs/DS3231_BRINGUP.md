# DS3231 RTC bring-up — M4, NOT SENSOR/NVS VERIFIED

> **Current command availability:** `diag_rtc` and `diag_i2c` exist; use `M4_DIAGNOSTIC_COMMANDS.md` after pin/voltage review. Earlier absent-function wording below is HISTORICAL / NOT CURRENT for diagnostics, not permission to claim RTC/NVS validation.

Prerequisite: reviewed I2C pins/3.3 V pull-ups, identified module and battery/charging behavior, approved RTC **sensor-only** firmware. Current HW_SAFE does not scan/set/read a real RTC; no `i2cdetect` command on Jetson can interrogate a chip wired to ESP32.

Connections: power off, reviewed SDA/SCL/VCC/GND only, appropriate backup cell if supported; servo/pump disconnected. Verify module pull-ups are not feeding 5 V into ESP32 and cell is safe for the breakout circuit.

Commands: physical discovery/read/set functions are **not implemented in this pack**. After approved bounded I2C/RTC test firmware is available, use its reviewed scan/read/set interface and `pio device monitor --port ACTUAL_COM --baud 115200`; save raw clock/validity output in `evidence/rtc/` with hash. Do not use the Jetson's unrelated I2C bus as proof.

Test: discover actual address/device → read clock/validity/oscillator-stop information → explicitly set a recorded reference time/timezone policy → read back → restart MCU → remove/restore main power only if backup cell arrangement permits → compare elapsed time/retention → observed date rollover → invalid/unset/rollback time fails safely (not feeding-ready). Do not silently infer validity from a nonzero date.

PASS: correct identity/address, time/reference agreement within declared tolerance, reboot/backup/rollover evidence and invalid-time handling. FAIL: bus errors/wrong pull-ups, impossible dates, lost time, unsafe battery behavior or invalid RTC reported ready. Test NVS/daily portions/grams/cooldown and interrupted-feed lockout **later** with reviewed integration; host persistence tests do not count. Next gate: food-level sensor.
