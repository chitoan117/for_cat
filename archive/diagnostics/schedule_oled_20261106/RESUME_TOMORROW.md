# STOPPED AT OWNER REQUEST — 2026-11-06

Owner explicitly requested stop here and continue tomorrow. No further hardware testing, calibration, schedule creation or source synchronization was performed after that request. No live test plan has been created, so no temporary feeding schedule needs cleanup.

## Deployed so far

- ESP32 app SHA256 f97d42d346bfd7957fec1f38c5e0e9bde17e9802a1b38490d2411edfcf65deab. Source here: esp32/esp32.ino. Flash/verify PASS, prior app backed up on Jetson, old NVS unchanged before first execution. Schedule history namespace is allocated lazily on the first scheduled command, separate from scale calibration.
- Same accepted servo1350us/900ms OPEN,1600us/1450ms CLOSE,1500us neutral; same E1<=30cm and35g mass threshold.
- OLED second line now AI:CAT / AI:DOG / AI:FAIL from real AI heartbeat only, with4s expiry. Manual/button feeding no longer fabricates a CAT label. Retains weight and four sensor labels.
- MCU feed_once ID protocol: persistent32-ID history before motion, ACCEPTED/DUPLICATE/BUSY/REJECTED ACK; terminal weight-result event. Scheduled feed uses weight timeout rather than4s manual bench timeout. No scheduled command has been sent on real hardware yet.
- Jetson worker migrated UNIQUE(plan_id,local_date) to UNIQUE(plan_id,due_unix_ms), preserves old IDs/receipts. Renaming/retrying same slot dedups; editing time to a new slot can execute again that day. Root observed cause:16:33 slot ran, owner edited same plan to16:35 and old daily identity skipped it.
- Bridge durable scheduled delivery waits for readiness/new protocol, retries SAME ID awaiting ACK, commits dispatched only after MCU ACK, stops expired requests after existing1minute window, records result/uncertainty without replaying accepted attempts. Retains DOG confirmation>=.7,3 distinct observations,1second. Independent raw AI OLED publication does not weaken actuator DOG confirmation.
- Backend files already replaced on Jetson: /home/toan/for_cat/jetson/tools/fc_live_bridge.py and app/scheduled_worker.py. API/bridge restored; firmware reported READY, sensor=1, inspect_lock=0,moving=0. No direct motion/feed command sent during deployment. UI/frontend unchanged.
- Backups and deployment evidence: /home/toan/for_cat/evidence/schedule_oled_20261106; events.before.db is a consistent SQLite backup before migration. Original sources under before/. Do not restore the DB casually: it would discard subsequent user changes/events.

## Validation completed

-30 worker/slot migration tests PASS on isolated app copy and temporary DBs;2 legacy tests deselected (old retime semantics intentionally superseded and separate C++ synthetic transport test).
-5 bridge tests PASS with real SQLite/fake UART: busy/retry/ACK/restart, expiry/protocol/stale/inspection, missing result uncertainty, independent OLED/DOG filtering, CAT/manual transport.
-Native extracted firmware tests PASS: old servo/pin/mass regressions plus ACK/durable duplicate across simulated reboot/busy/HX/storage/inspection guards, scheduled weight path beyond4s, OLED CAT/DOG/FAIL expiry and rollover.
-Arduino compile PASS:394465 program bytes,35840 global bytes. Actual new MCU protocol1 and ai_oled FAIL observed in live bridge telemetry.

## Pending tomorrow

1. Owner had said ready for real schedule test, but final live scale reading was about-26.24g, consistent with bowl removed. New MCU reported tare_counts=-695205.8666666667 and grams_per_count=-0.000945082600219258. No retare was done. Owner was asked to place empty bowl back and confirm near0g; instead requested stop. Start by confirming bowl physically in place, no pressure, proper0g. Do NOT tare with bowl absent or with food present.
2. Perform one supervised live timed feeding, camera empty so AUTO_CAT cannot add another cycle. Create a temporary future plan through /api/meal-plans after confirming physical readiness, monitor occurrence -> same-ID UART command -> ACK -> measured result. Remove that temporary plan via soft-delete after test, even on timeout. Do not alter existing owner plans. Current owner plan previously enabled Friday16:35; re-read before any change. Never catch up an old missed meal automatically.
3. Confirm physical OLED CAT/DOG/FAIL if owner can show real recognition; software and live FAIL verified, physical CAT/DOG display not yet owner-confirmed.
4. Download deployment.json/flash_result.json/NVS evidence and final worker log from Jetson to this folder. Inspect current checksums before edits.
5. Original Windows sketch D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino has NOT yet been synchronized to this new firmware (still previous balanced version, SHA256 e13148abd1b39c7c0e13222b73918079d671b9b17d80bf1d4af27d3729806a3f). After final checks, hash-guard then copy the deployed source from this folder; do not overwrite unrelated owner edits. Backend candidate files here match deployed files.

SSH: toan@server-jetson.local, key C:/Users/chito/.ssh/opencode_jetson, HostKeyAlias192.168.123.13, StrictHostKeyChecking=yes,BatchMode=yes. Current LAN web http://192.168.1.6:8000/app. Use escalated shell for network/external source writes as before. Do not use Windows for_cat placeholders as actual source; actual backend lives on Jetson.
