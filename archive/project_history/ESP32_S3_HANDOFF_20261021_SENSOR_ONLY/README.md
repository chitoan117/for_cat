# FOR_CAT — current hardware sensor-only handoff — 2026-10-21

Source updated on Windows Git mirror, main/ac17065 + preserved dirty changes.
Jetson SSH hostname is unavailable: these edits are NOT already deployed there.
No commit/push/flash/physical actuator operation performed.

## Open these first
- `source_snapshot/docs/CURRENT_PROJECT_STATE.md`: audited actual/planned status.
- `source_snapshot/docs/ESP32_S3_SENSOR_STATION.md`: CURRENT GPIO table, candidate
  pins, Windows/Jetson build/flash/monitor commands, next isolated scale test.
- `source_snapshot/docs/ROADMAP.md`: phased TODO and acceptance gates.
- `verification_current.json`, `checks_final/summary.json`: actual current tests.
- `physical_report_NOT_TESTED.json`: all current physical tests NOT_TESTED.

## Firmware for the NEXT single physical test
`deploy_hx711/` is current ESP32-S3 16MB/noPSRAM ASCII diagnostic at115200,
HX711 DOUT4/SCK5. Servo6 and pump7 remain untouched. Use the manifest hashes;
factory image covers NVS/gaps, so review/backup before deliberate flashing.
The station document gives ROM16MB preflight, no-stub and verify commands.
Reference masses/tolerance/installation must be physically confirmed.

## Validation (software, NOT physical PASS)
378 Python;140 safety+3351 driver assertions;6 actual loop cases/142 assertions/
22 reports;26 process E2E cases;7 UART vectors;40 guards;21 firmware profiles;
native fuzz2000/12000 assertions and Python parser fuzz1000. UBSan canary verified
and native/process checks pass. Host C++14 shadow250028checks. No new ASan PASS.
Ruff and git diff --check pass. Default repository dataset check excludes the
external Windows video corpus; it does not claim the22video/165pilot is absent.

## Scope
This pass updates canonical state/roadmap and the safe sensor pin subset. Full
closed-loop pulse actuation, CAT-near feed arbiter, trend eating FSM,4-sensor
inventory, telemetry-to-DB/API, kiosk/app and schedule sync are tracked TODOs,
not represented as already integrated. No new EATING NN required now.

HC-SR04#2 and JSN#2 pins remain unassigned. Candidates1/2 and21/47 are report-only
pending owner/header validation;48 excluded due generic RGB LED. Do not use old
V2 diagnostic6/7/10/11/button12/buzzer13 mapping on the newly selected wiring.

`source_snapshot` has no .git and is a reviewed source snapshot, NOT permission
to overwrite `/home/toan/for_cat`. Compare actual Jetson branch/dirty changes and
selectively synchronize; preserve working detector/engine/binary and backups.

`audit/final_tracked_diff.patch` includes PRE-EXISTING V3 work as well as this
update. `audit/preexisting_uncommitted.patch` records the baseline. Never blindly
apply the entire patch to an unknown remote tree.
