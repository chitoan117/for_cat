# Integrated ESP32-S3 manual candidate — actual build result

2026-10-30. **Candidate prepared YES; flashed NO; physical PASS NOT_RUN.**
Location: `D:\for_cat\REAL_HARDWARE_EXECUTION_20261030\INTEGRATED_MANUAL_CANDIDATE`.

## Result / selected image

| Item | Actual result |
|---|---|
| Existing suitable combined image | None identified in reviewed locked kit: servo/pump/sensor environments are separate; shipped pump INERT; current running image still not proven from staging source |
| New integrated source | YES: `firmware/src/manual_station.cpp`, `include/manual_station_policy.h`, candidate-local sensor integration |
| Actual ESP32-S3 build | VERIFIED_PASS_BUILD_ONLY; `build_safe_txatomic/result.json` and `compile.log` |
| Selected APP image | `build_safe_txatomic/artifacts/firmware.bin`, **415456 bytes** |
| Image SHA256 | `77faf09775e55731b08c511ac852273b9839963c081ebe924035f8f9aecaac93` |
| GPIO6 servo | READY in firmware for approved **small bounded bench** after safe flash; real movement NOT_RUN, endpoints not measured |
| GPIO7 pump | **BLOCKED_POLARITY**: current image INERT, no GPIO7 writes. Conditional active build supported after actual OFF0/1 evidence |
| GPIO2 buzzer | Disabled/untouched on boot; explicit manual driver review/test only, no production DOG rule |
| Hardware | No Serial, reset, flash, service mutation or actuator operation executed by agent |

Do not use `build_safe_initial`: it predates the telemetry-queue correction. Previous outputs/failures remain evidence. Only the selected image/hash above is handed off.

## Reuse / build evidence

- Snapshot76 existing files; all original snapshot inputs remain unchanged. Existing HX711, quad-ultrasound scheduler, PIR, OLED/button and bounded servo/pump controllers reused.
- Servo/pump controller headers retain original SHA256s recorded in `verification_tx_atomic/result.json`.
- Windows PlatformIO6.2.0.post1, espressif32 55.3.311, Arduino3.3.11/IDF5.5.5, Xtensa14.2.0. UART0/115200, ESP32-S3 chip9, flash16MB/DIO80MHz, no PSRAM. Actual `image_info.log`: checksum and appended validation hash valid, secure_version0.
- Partition table matches existing sensor kit **byte-for-byte**; app fits0x640000 partition. Build offset0x10000 is metadata, **not proof of actual running bank or flash authorization**. No bootloader/table/NVS/otadata artifact is released for writing; PlatformIO's internal factory binary is not the handed-off image.
- **30 new integration cases SIMULATION_PASS**, including both hypothetical OFF polarities in host fakes only: boot/no auto output, mutual exclusion, bounded pulse/limits, sequence replay, reconnect budgets, nonblocking UART deadline, time regression, malformed input, sensor/calibration preservation and manual-only buzzer.
- **37 complete telemetry frames checked; maximum4812 bytes ≤8192**. Initial checks exposed queue collision/partial output; candidate now defers a full frame until its bounded nonblocking queue is empty. Failed runs retained; final selected regression is `verification_tx_atomic/result.json`.
- `handoff_checks/` checks NEW console/flash-plan refusal and build/source identities. Its73 checks include hashes and helper assertions, not73 physical tests. No old qualified suite was rerun. `RELEASE_RECEIPT.json` binds selected image/build/source/helpers.

## Manual control authority and limits

Boot: servo DISARMED/PWM off; pump default unknown-polarity INERT/high-Z; buzzer untouched/disabled; all ultrasound channels disabled. High-Z is **not measured pump OFF**: isolate pump load power for the default image. Nothing reacts to CAT/DOG/button/reconnect by moving an output.

- Servo reuses configure-once,1000–2000us electrical bounds, **span≤100us**, max3arms/moves per boot, arm2s/move250ms/close350ms/hard3s limits. ARM itself may move toward configured CLOSE. Full white-gate OPEN/CLOSED endpoints/angles remain unmeasured; do not claim a100us bench is a calibrated full-gate test. No sweep or invented0/90/180deg.
- Pump-active source reuses20–500ms/max3pulses/≥1s cooldown/2s arm expiry, with exact measured OFF polarity compiled in. No active pump image was built without evidence. Servo/pump/buzzer cannot be ARMED/active simultaneously.
- UART commands are fenced by boot nonce, per-session generation and increasing sequence; a session restart never resets budgets/configuration. Stale/duplicate command while active fails closed; invalid/oversize input, TX overflow, clock regression and output failure latch station fault.
- Bare `stop` (or `servo stop`) commands immediate PWM/pump OFF and latches fault; no command clears/re-arms that latch. Power cutoff and physical stop/closure remain external facts. Host loss does not extend embedded output deadlines. Physical timeout/current/OFF accuracy is not yet qualified.
- Nonblocking UART plus paused sensor/I2C work while outputs are active keeps long telemetry/report calls out of the active timing path. Sensor acquisition is disabled before ARM and never automatically resumed after a test.

### Protocol / operator console

Read-only: `status`, `servo status`, `pump status`. Operator starts `session begin`, receives boot/session identifiers, then sends:

```text
@BOOT_NONCE SESSION SEQUENCE servo configure MIN_US MAX_US CLOSE_US OPEN_US CONFIRM
@BOOT_NONCE SESSION SEQUENCE servo arm YES
@BOOT_NONCE SESSION SEQUENCE servo open
@BOOT_NONCE SESSION SEQUENCE servo close
@BOOT_NONCE SESSION SEQUENCE servo disarm
@BOOT_NONCE SESSION SEQUENCE pump arm YES
@BOOT_NONCE SESSION SEQUENCE pump on MS
@BOOT_NONCE SESSION SEQUENCE pump off
@BOOT_NONCE SESSION SEQUENCE pump disarm
```

These are protocol definitions, **not approved activation commands/values**. `manual_console.py` wraps envelopes and non-actuating keepalive for a human TTY; never auto ARM/ON. Default PLAN opens nothing. Execute requires a new specific owner approval, reviewed image SHA/flash receipt, inactive Bridge/free stable port and reviewed per-device parameters; the console never stops/starts services. STOP/QUIT/session end sends latched STOP, not reboot. Console real Jetson/Serial execution remains NOT_RUN.

Exact sensor commands (`ultra-select/off/multiplex/guard`, weight-stability) require the same envelope, no active outputs and ECHO electrical review. Existing drivers/mapping retained: HX4/5, OLED8/9, PIR11, button21, HC1 12/13, HC2 16/17, JSN1 14/15, JSN2 18/10; RTC disabled. No WATER_ROI or automatic feed.

## Calibration / NVS

Candidate cannot execute calibration save: NVS save adapter returns false; tare/cal/save/automatic refit commands are not routed. Partition/NVS contents are not changed by the proposed APP-only plan.

**APP flash/reset cannot preserve volatile RAM.** Before any reset, preserve exact current accepted coefficients/context from existing original evidence/current approved capture, or establish already-compatible persisted calibration. No approximate historical offset is embedded. Boot reads the existing sensor `m4-calibration/sensors-v2` key without migration; coefficients stored only under another key/RAM are not silently invented/copied. Authorized `hx import OFFSET COUNTS_PER_GRAM CONFIRM` restores exact owner values to RAM only, no tare/refit/NVS write. The console requires exact approved values for that command. Historical HX static PASS remains; no weight-series repeat is requested.

## Bridge/Web compatibility — explicit blocker, not hidden

Mode **diag_manual_station**, kit ID **FORCAT_MANUAL_STATION_20261030_V1**, kit_profile diag_manual_station, manual_station.schema_version1; existing sensor telemetry_schema_version2 retained. Manual PWM/pump states and sequence/session are explicit. Physical output feedback is unknown/null, never claimed OFF/closed from a command.

Current production Bridge intentionally rejects this new mode. Do not relabel it diag_current_hardware or use the old sensor profile to mask manual actuator state. Future read-only Bridge support must explicitly validate the new mode/manual schema,8192 bound/session/freshness/actual output flags, disable automatic/feed/DOG TX and propagate null/stale/source correctly to paired API/Flutter. No Bridge/API/Flutter deployment is part of this handoff. Returning Serial to the unchanged Bridge restores ownership/service, **not valid telemetry/Web qualification**; unsupported mode is expected until separately reviewed integration.

## One coordinated maintenance procedure — PREPARED, NOT AUTHORIZED/EXECUTED

1. Preserve accepted backup A/B and rollback app; no new16MB read. Bind actual running partition and security/eFuse/anti-rollback to this board/boot and both old/new images. Existing metadata app0 is not runtime proof. Read-security/ROM/reset are impactful and need their own approved scope before use.
2. Review four ECHO protection/peak evidence, servo/pump supply/driver/common-GND/cutoff and physical load isolation; preserve exact HX coefficients before reset. No new request to repeat GPIO/service/GCC/AI/HX accuracy PASS.
3. USER approves a **single coordinated read/APP-only maintenance scope** (with a separate explicit write decision before step4), records original Bridge unit/exe/PID/AI/API state, then releases only `for-cat-esp32-bridge.service`. Use current PID for ownership checks, never kill historical4067. `fuser` must show port free before exactly one approved Serial tool. No camera/AI/API restart. Existing read-only lease is not flash permission and must not be treated as one.
4. Capture actual normal-boot running-bank evidence and approved ROM security/eFuse evidence; close each tool before the next. If gates pass, review NEW flash approval binding this selected image SHA/layout. **`flash_plan.py` is offline only**, reuses existing backup/bank/security/rollback validation and adds this image/protocol/pump/HX binding. No review -> no write argv. Only a separately reviewed, compatible esptool executor/actual port is accepted; do not auto choose installed3.3.3 as flash executor.
5. Only after USER write approval, execute the generated **one APP offset** write/verify arguments. No bootloader/table/NVS/otadata/erase or factory binary. The validator currently supports only verified app0/unrestricted unsigned/unencrypted/secure_version0 policy; other actual bank/security -> STOP/review, not force. Existing review template fields/old validator gates are prerequisites, not facts inferred from build0x10000.
6. Approved normal boot; capture exact candidate identity/mode/default DISARMED/pump INERT/buzzer disabled and sensor validity/ages. Verify image bytes at executor first; firmware ID alone is not binary hash proof. No automatic actuator command. Under separate activation approval, use human console for servo small-motion, then separately gated pump/buzzer, never automatic food dispensing.
7. Close all Serial tools, confirm normal app boot and release port. Restore **only originally active Bridge** to the same binary/unit; verify fresh sole-owner PID and AI/API unchanged. Do not claim telemetry PASS if original Bridge rejects new mode.
8. If candidate boot/identity fails, stop for review: the existing rollback app381984bytes/SHA `820cdeecde2c4af7b7b2c7f4a1090a3b5c775809886df662522a44e83a4b9826` is the APP-only fallback at the **same verified bank**, using generated rollback/verify arguments. Restore does not recover RAM calibration; bank/security/ROM access must already be reviewed. No blind flash loop/full erase. External cutoff is the response to jam/unexpected flow or an unresponsive console.

Remaining actual evidence before flash: running bank/security/eFuse/recovery/executor review, four ECHO protection peaks, load-power/GND/cutoff, exact calibration preservation and explicit flash approval. Servo endpoint/power supervision and pump polarity/priming additionally gate movement. None is self-approved by the build.

## ONE next owner action

**Updated owner priority: servo first using this existing image. Pump polarity is not a prerequisite for the servo bench if the pump load-power path is physically isolated.**

First identify and isolate the **pump motor/load supply branch at its supply switch/connector**, without disconnecting ESP32/Jetson power, USB, GPIO7 or the shared logic ground. Do not remove loose powered conductors. Send a photo showing source→F5305S→pump, the exact load-power isolation point, and the supply/driver labels. If the separate load branch cannot yet be identified, send that wiring photo before changing connections. This closes only the load-isolation gate, not bank/security/flash permission or proof of pump OFF polarity.

Later pump qualification needs actual OFF0/1 and boot/reset/high-Z bias evidence on the real PCB with motor isolated, using a reviewed compatible low-voltage stimulus and safe dummy load/measurement setup. Do not infer polarity from module name/datasheet or test the motor before supply/wiring review. Once measured evidence is reviewed, `build.py --label NEW_LABEL --pump-observation ACTUAL_FILE.json` can create a separate pump-active APP. This is not needed merely to begin the servo path. No need to repeat mapping, services, AI, GCC or HX weights.

**APP FLASH NO-GO. Servo firmware bench READY / physical activation BLOCKED pending gates. Pump BLOCKED_POLARITY. Buzzer production DISABLED. Aim35g/final30–40g inclusive reserved for a separately approved future closed-loop trial.**
