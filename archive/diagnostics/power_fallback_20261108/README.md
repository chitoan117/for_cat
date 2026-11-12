# Power-failure fallback candidate â€” 2026-11-08

Owner requests autonomous feeding during Jetson power loss: E1<=20cm plus PIR,35g measured close. Owner clarified ESP32 currently draws USB power FROM Jetson. There is no confirmed independent supply for ESP32/servo/HX711/E1/PIR. Therefore a power outage currently removes the controller's power too; software cannot provide continuity. Owner subsequently explicitly requested flashing now and will obtain independent power tomorrow. Firmware and matching bridge have now been deployed and backup_on persisted. A real physical outage test remains pending independent power. Current app554dd2c2251f27245dcdb98f14c5d07932a38e656282deb676b5451bffc0a48d; prior OLED app10ab2337... is a backup. Original Windows sketch and new FallbackGate.h were synchronized after hash guard and backup.

## Implemented behavior

- Separate explicit jetson_ping heartbeat every1.5s in bridge, independent of AI labels/camera. Serial writes do not add periodic heartbeat rows to the events DB.
- Backup waits30s after MCU boot and15s without host heartbeat. It does not infer power loss merely from a missing CAT/DOG detection.
- Fresh E1 readings2..20cm across3 distinct frames, PIR HIGH>=200ms, fresh calibrated empty-bowl scale within+/-2g, idle motor, no inspection lock, no STOP/pause and no active calibration/alarm are required.
- Uses the existing measured feed branch: same1350us900ms open,35g delta triggers1600us1450ms close, then1500us neutral. Existing25s no-dose timeout remains. Do not claim exact physical35g accuracy; moving food and the loadcell must be physically checked.
- Persistent separate fc_backup_v1 namespace saves inflight marker BEFORE motion. Completion only clears inflight when a full timed close is recorded. A reboot during an unfinished attempt raises existing inspection lock. Operator inspect_ok after actual alignment acknowledges it.
- No repeated feeding while a nearby animal remains. Rearm requires fresh E1>30cm and PIRLOW continuously5s, plus>=5min since previous attempt. Reboot with a completed latch conservatively restarts cooldown. Missing/faulty readings never count as a clear zone.
- Factory/default firmware setting is DISABLED; this installation has been explicitly ENABLED at owner request. backup_on/off persist enable state. Owner knows independent power is not available until tomorrow. Candidate OLED header shows BACKUP in offline backup mode; it does not fabricate AI CAT/DOG labels.

## Files and validation

- esp32/esp32.ino and esp32/FallbackGate.h: integrated firmware candidate based on verified OLED product source.
- fc_live_bridge.py: matching independent heartbeat candidate. Do not deploy firmware enabled without deploying this companion bridge, or a running Jetson could look absent.
- test_gate.cpp covers20cm boundary, three-distinct-frame qualification, PIR/host/scale/STOP guards, repeat suppression, delayed departure rearm, stale rejection and unsigned clock rollover.
- Native test result and full ESP32 compile result are recorded separately. No real outage, servo movement or physical backup-power test has been performed in this task.

## Hardware facts still required

Need actual backup source type, rated voltage/current and PCB supply routing before giving concrete wiring instructions or enabling the feature. Backup must supply ESP32, E1/PIR/HX711 and servo at their appropriate regulated voltages, with suitable servo current and shared signal reference. Existing Jetson USB must not be treated as an independent backup source. PIR only detects motion; E1 measures20cm. Without Jetson AI, this mode does not distinguish a cat from a dog or another moving object.

## Final verification13:38

- ESP32 compilePASS:398817 bytes,35880 globals. Two native test suites PASS (decision gate and actual adapter persistence/heartbeat guards).10 bridge tests PASS including independent heartbeat with missing AI.
- Actual previous app,partition table and OTA sequences matched before write; new app write/verifyPASS. NVS unchanged by flashing before first execution. Separate backup namespace and enable setting are additive after boot; scale calibration remained unchanged.
- AtMCU uptime55s:backup_enabled=true,backup_offline=false,backup_storage_ok=true,backup_wait_clear=false,backup_active=false,READY,OLEDHEALTHY. Confirms Jetson heartbeat beyond boot grace; all3 servicesactive. No feed/open/close command sent during deployment.
- Live bridgeSHA256576e1755b1623ba8499cb3bd42f217f4828d675cfa0add88ef7e47f64ab73ec2. SourceSHA256cbfd8c3d7a7187fdb0e89edf8fbcde52c69b67f6d8cabaca7046ee72d68c30e6; headerSHA2562c50b886e8218b12d678f34c06bb3e98b05bd586119ff7dea8e54db88a3ab21e.
- Live scale around73.34g; not empty. Do not tare without a new empty-bowl confirmation. No physical fallback feeding was attempted today. Power-source type/current and real outage/dispensing accuracy remain unverified.
- Backup evidence remote:/home/toan/for_cat/evidence/power_fallback_20261108; localdeployment.json,flash_result.json,backup_result.json.

## Subsequent CAT latency update

At13:55 owner requested faster CAT+E1<=30cm response. New deployed app6012fe3f5011aca92449dea620ec870b68e67b22a66641aa0fdbb360f027396f prequalifies two fresh E1 samples; backup20cm+PIR block is unchanged and remains enabled. See ../cat_response_20261108/README.md. Use that app as the current flash baseline; this folder's554dd2c2... app is a previous backup.
