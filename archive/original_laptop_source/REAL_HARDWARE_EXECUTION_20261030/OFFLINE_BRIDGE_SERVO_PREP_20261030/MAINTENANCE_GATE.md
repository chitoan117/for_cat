# APP-only gates — source/evidence review, no device execution

## Retain existing PASS / owner statements

- Candidate415456bytes, known SHA77faf097…aecaac93; actual build and30 host regressions retained, not rerun.
- Partition table matches baseline; backupA/B16MB and rollback app381984bytes/SHA820cdeec…3a4b9826 accepted. Do not request another backup read or trial restore.
- GPIO6servo/7pump/2buzzer and HX static accuracy accepted; AI and three services previously OWNER_CONFIRMED. Do not requalify them to refresh dates.
- **NEW OWNER_CONFIRMED:** both motor wires removed from F5305S OUTPUT; GPIO7/GND unchanged; shared supply5V–10A. Pump motor load isolated for servo. OFF polarity remains UNKNOWN but does not block servo with motor isolated. No new photo of that completed step requested.

## Remaining real gaps and one next check per gap

| Gate | Evidence state | Next targeted check (not all requested now) |
|---|---|---|
| Servo supply/GND/load cutoff/model | Supply rating OWNER_CONFIRMED; servo-specific wiring/model/cutoff not evidenced | One servo label+wiring/cutoff photo; then select the needed voltage check from actual terminals/rating |
| Safe CLOSE/OPEN pulses/mechanism | NOT_MEASURED; firmware span≤100us | After safe flash and specific activation approval, one bounded supervised small-motion trial; record pulse/video, not guessed angles |
| Four ECHO13/17/15/10 | Protection/peak evidence not located | Review the actual four protection circuits/values and existing peak captures; any new trigger/peak measurement needs its approved electrical scope |
| Exact HX calibration preservation | Static PASS; persistence NOT_VERIFIED | Attach existing exact offset/factor/calibration context; acceptance JSON gives factor-1064.4473 but latest offset only approximately-698922.87, insufficient for exact restoration |
| Actual running bank | NOT_VERIFIED; metadata app0 not runtime proof | Approved normal-boot capture of loaded app offset, board/boot-bound; no reset now |
| Security/eFuse/antirollback | NOT_VERIFIED | Approved bounded ROM/security summary bound to this board and old/new secure_version0 images; not a passive GET |
| Recovery/executor/handback | Rollback bytes PASS, hardware access/tool route not fully qualified | Review physical BOOT/EN access and exact executor/port/recovery sequence before authorizing the window; do not test-flash as proof |
| APP-only and movement authority | No current approval | Separate explicit approval after evidence review; pump isolation confirmation alone grants neither flash nor movement |

No claim that5V–10A guarantees servo voltage at terminals or immunity to stall/brownout. Do not power down/reset ESP32 to obtain photos or lose RAM calibration. No tare, refit, save or NVS migration.

## Commands PREPARED ONLY for a later authorized maintenance

Existing read-only tooling is in `HARDWARE_PHYSICAL_BRINGUP_20261029/maintenance_readiness`; remote `M` must be the verified actual staged directory, not an assumed transfer. The old read lease cannot authorize flash.

```bash
# ONLY after physical prerequisites and separate read-maintenance approval:
python3 -B "$M/serial_window.py" --execute OWNER_APPROVED_READ_MAINTENANCE --approval "$M/ACTUAL_OWNER_READ_APPROVAL.json" --output "$WIN"
# In the approved open lease, second terminal; boot capture itself does not reset:
python3 -B "$M/boot_capture.py" --execute OWNER_APPROVED_BOOT_CAPTURE --lease "$WIN" --seconds 60
```

USER normal-boot/reset action is separately reviewed; capture `Loaded app from partition at offset ...` if actually emitted. Do not infer bank from an OTA table or flash an image merely to add status.

Existing reviewed Jetson esptool3.3.3 read-security syntax, **not executed here**; each port tool closes before the next:

```bash
# Within approved lease; PORT=the verified stable by-id; logs NEW, no clobber:
( set -C; python3 -B -m esptool --chip esp32s3 --port "$PORT" --baud 115200 --before default_reset --after no_reset --no-stub get_security_info > "$WIN/security_info.log" 2>&1 )
RC=$?; printf 'SECURITY_EXIT=%s\n' "$RC"
( set -C; espefuse.py --chip esp32s3 --port "$PORT" --baud 115200 --before no_reset summary --format json --file "$WIN/efuse_raw.json" > "$WIN/efuse_console.log" 2>&1 )
RC=$?; printf 'EFUSE_EXIT=%s\n' "$RC"
python3 -B "$M/security_flags.py" --source "$WIN/efuse_raw.json" --output "$WIN/selected_security.json"
```

These commands can enter ROM/reset; no stub fallback/burn/erase/debug. Confirm efuse_raw.json is NEW too before the file-writing command; keep full eFuse JSON private. Installed3.3.3 is not automatically an approved APP flash executor. Missing/restricted flags remain blocked, not disabled.

After tools close and approved normal app boot, the lease handback token is `NORMAL_APP_BOOT_AND_PORT_TOOLS_CLOSED`. Existing coordinator restores only originally-active Bridge and checks fresh sole ownership/AI/API continuity, preserving original unit/executable. It does not prove valid app telemetry. No kill of historical PID4067.

APP-only stage is a separate reviewed write decision, using the existing candidate's **offline** `flash_plan.py` with actual review file and `build_safe_txatomic/result.json`. It withholds write argv unless bank/security/backup/image/calibration/electrical/recovery gates pass. Its supported branch is verified app0/unrestricted unsigned-unencrypted/secure_version0; other bank/policy stops for review. No executable write command supplied while these facts are missing. Only APP at verified bank; no factory/bootloader/table/NVS/otadata write. Rollback uses existing original APP at that same verified bank, not erase/full-flash.

After candidate boot/identity/bytes verification and separate servo activation approval, use SERVO_TEST_READY.md. Close all serial tools and hand back original Bridge after the approved window; existing production Bridge still rejects new manual mode until separately reviewed deployment. **No maintenance/device/service command in this document was executed.**
