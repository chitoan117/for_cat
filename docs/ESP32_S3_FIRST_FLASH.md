# First flash — bridge-first HW_SAFE only (NOT HARDWARE VERIFIED)

Prerequisite: exact module/board/USB routing identified, power reviewed, N16R8 compile options checked against the physical part. If identity or routing is unclear, stop—do not flash based only on a seller title. Run PC commands from the **project root**; replace COMx with observed COM. All commands below are future manual commands; none uploads hardware in this pack.

1. **No sensors connected.**
2. **No servo connected.**
3. **No pump connected** or actuator rail energized.
4. Attach the connector identified as CH343G USB-to-UART using a data cable.
5. Detect COM: `& .\.venv\Scripts\python.exe -m serial.tools.list_ports -v`; save port/device IDs.
6. Build bridge HW_SAFE:
   ```powershell
   $Pio = Join-Path (Get-Location) '.tools-venv\Scripts\pio.exe'
   & $Pio run -d esp32 -e esp32s3_n16r8_hw_safe_uart
   Get-FileHash -Algorithm SHA256 .\esp32\.pio\build\esp32s3_n16r8_hw_safe_uart\firmware.bin
   ```
   This profile selects UART0, CDC-on-boot=0, HW_SAFE, actuator flag 0 and a human boot banner. It remains **COMPILE SURROGATE ONLY**, not verified seller pin compatibility.
7. After successful build and board review:
   ```powershell
   $Port = 'COMx'
   & $Pio run -d esp32 -e esp32s3_n16r8_hw_safe_uart -t upload --upload-port $Port
   ```
   If automatic boot entry fails, consult the exact board BOOT/RESET procedure; no pin bridging or random wiring.
8. Monitor at 115200: `& $Pio device monitor --port $Port --baud 115200`. Opening DTR/RTS may reset the board; if necessary press the identified RESET button while monitoring.
9. Record ROM output where available and the optional once-only `FORR_CAT` line. Require version/profile/board label, `actuator_enabled=0`, `simulation=0`, `safety=SAFE_BUILD_ACTUATORS_DISABLED`; save screenshot/log and image hash. **Close monitor (Ctrl+C)** before protocol probing. Banner absence is a troubleshooting item, not invented success.
10. From `jetson/`: `..\.venv\Scripts\python.exe -m tools.test_serial --device COMx --m3 --count 3 --interval 1 --json`.
11. The same probe sends GET_STATUS. Require PING→ACK `01`, GET_STATUS→SYSTEM_STATUS `01`, correct IDs and CRC. Status `01` means protocol responsive only; UART v1 contains **no build metadata or sensor health**.
12. Unplug physically. Record disconnect time and COM disappearance; run one probe against the old port, require failure/timeout and no fabricated PASS.
13. Reconnect physically, record time, rediscover COM (may change).
14. Repeat the same low-rate probe against the rediscovered port; require PING and GET_STATUS recovery.
15. Record individual PASS/FAIL and all evidence. PC flash/serial success does not by itself constitute M3; the physical Jetson↔ESP32 link is required.

No FEED_REQUEST option is added to the probe: v1 cannot prove the flashed profile from status, so automatic/optional host feed testing is inappropriate for this first gate. Existing HW_SAFE dispatch internally rejects feeding; no need to test it physically to pass M3. Do not use SIM firmware for physical gate evidence. Native CDC profile `esp32s3_n16r8_hw_safe` remains available but is not the CH343G first-flash target.
