# FOR_CAT ESP32 servo port from owner-tested UNO sketch — 2026-11-03

The supplied photos show the servo mounted beside the hopper outlet, driving the gate above a gravity chute. They do not establish speed or end positions. The owner reports that the supplied UNO sketch works on this mechanism.

The ESP32 candidate uses the actual UNO constants, rather than its stale menu/comment timings:

| Operation | Signal | Duration | ESP32 command |
| --- | --- | --- | --- |
| Open right | GPIO6, 1400 us | 1100 ms | `3` or `servo_open` |
| Close left | GPIO6, 1600 us | 900 ms | `4` or `servo_close` |
| Fine close | GPIO6, 1600 us | 170 ms | `servo_fine_close` |
| Fine open | GPIO6, 1400 us | 170 ms | `servo_fine_open` |
| Stop | GPIO6, 1500 us neutral hold | Until next movement | `0`, `stop`, `STOP` |

Motion commands use the existing newline-delimited serial protocol (115200 baud). A standalone `0` at the beginning of a command is handled immediately without waiting for a newline. Existing `1` and `2` remain CAT and DOG, because the live Jetson bridge sends those commands. They do not mean fine adjustment on ESP32.

LEDC remains 50 Hz / 14 bits. After a movement, neutral PWM stays attached, matching UNO `writeMicroseconds(1500)` behavior. Idle checks now distinguish rotation from neutral hold so the next cycle and calibration are not blocked. Boot remains detached; there is no new startup motion. Failed neutral writes fall back to detaching PWM.

Existing automatic/manual feed paths use the new full-stroke pulses and defaults. Meal-weight and sensor logic remain outside the servo port. The GPIO47 limit switch remains disabled as requested. Physical closure and actual dispensed grams are not inferred from elapsed motor time. `open_ms` / `close_ms` adjustments are RAM-only (100–5000 ms); restart restores 1100/900 ms.

Manual servo commands reject a new movement while busy, while a DOG alarm is active, or while calibration is running. Explicit manual adjustments do not clear an existing inspection lock or resume a demo exited with `0`. The normal existing `inspect_ok` / `start` workflow remains applicable to subsequent CAT operation.

Validation: `test_servo.py` extracts the actual LEDC class and motor control functions from the candidate and runs them against fake hardware. Checks cover pulses/durations, neutral hold/reuse, fine moves, busy rejection, feeder open/close, STOP, millis rollover, HX-failure close, input bounds and write-failure fallback. See `native_test_result.txt`. This is host verification; mechanical operation on ESP32 remains untested.

`esp32.original.ino` is the exact source backup; `change.diff` records the delta. `output/` contains the ESP32 build artifacts after successful compilation.

## Authorized deployment and remote-access preparation

On 2026-11-03 the owner explicitly requested flashing and remote access while the PCB is being rebuilt. The binary SHA256 is `4c6c1d472d1be303c92b0bf4b5485b3f1669957396a0cb8de24c609f49a4fef8`.

Jetson `/dev/ttyACM0`: first 0x150000 bytes backed up; actual partition table matches the build; valid OTA seq1/seq0 selects app0. Only app0 at 0x10000 was programmed. Esptool verify passed. NVS readback is byte-identical to its backup. The new UNO-profile boot banner and TIMED/GPIO47-disabled telemetry were observed. Only a stop (`0`) and read-only mode/limit commands were sent; no servo movement commands were sent. See `deployment_evidence/flash_result.json` and `boot_verification.log`.

The ESP32 bridge is deliberately left stopped during PCB work so AI/scheduled requests cannot dispatch actuator commands. The API remains running. Hardware readings in the web become stale/unknown until the bridge and assembled hardware are requalified. Resume the bridge only when the owner is ready for PCB testing; opening serial can reset the MCU.

Local web readiness passed: `/app`, Flutter bootstrap/main JS, `/api/status` all HTTP200; same-origin WebSocket HTTP101. No hardcoded HTTP LAN URLs were found in the compiled frontend. These checks are not a remote/4G pass.

After owner login, operator grant and Serve/HTTPS account confirmation, Tailscale 1.104.5 is Running at `100.109.77.47`. Private Serve is enabled in the background, proxying `https://server-jetson.taila0ed37.ts.net/` to `http://127.0.0.1:8000`. The application URL is `https://server-jetson.taila0ed37.ts.net/app`. No Funnel config is enabled. Daemon logs confirm the ACME certificate was obtained.

Local application/assets HTTP200 and same-origin WebSocket HTTP101 were verified. HTTPS self-connections from the Jetson are inconclusive (connection refused with a listener explicitly bound to `%tailscale0:443`). Tailscale 1.104 intentionally binds Serve to that interface; see https://github.com/tailscale/tailscale/issues/21737. No interface-binding bypass was enabled. The iPhone subsequently joined the tailnet and responded to a Jetson Tailscale ping. The owner then explicitly confirmed that the HTTPS web displays normally on 4G/5G with Wi-Fi disabled. Remote web acceptance is therefore owner-confirmed; it is not an agent-observed phone/browser session or a physical actuator test. See `deployment_evidence/remote_access_result.json`.

Phone test: install/enable Tailscale, sign into the same authorized tailnet, disable Wi-Fi, enable 4G/5G, then open the HTTPS app URL. Jetson must stay powered and connected to the internet. Bridge remains stopped during PCB work; do not interpret remote UI access as successful physical feeding.

## 2026-11-04 startup inspection

Jetson was reachable at `server-jetson.local`, now LAN `192.168.123.3` (previous `.13` timed out). Read-only inspection found `Linger=yes`; AI/API/ESP32 bridge all enabled and active; user units target `default.target`. NetworkManager and tailscaled are enabled; the wired Ethernet profile has autoconnect enabled. API `/app` returned HTTP200 and the saved private Serve route remained configured. No Wi-Fi device/profile appeared in the inspected NetworkManager output, so current network operation is Ethernet, not confirmed automatic Wi-Fi.

The bridge is now active again after the machine's recent startup. The earlier PCB-maintenance stop was temporary and does not survive a reboot because the unit remains enabled. No service start, motor command, firmware flash or reboot was initiated during this inspection. AI currently has `Restart=no`; startup enablement is distinct from recovery after a later AI process failure.
