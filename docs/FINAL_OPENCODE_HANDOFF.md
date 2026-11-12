# FINAL OPENCODE HANDOFF — for_cat real sensor bring-up

**M4 SOFTWARE READY, PHYSICAL SENSOR VALIDATION NOT YET PERFORMED**

This is the pre-quota source/script/command freeze, not a hardware milestone award. Architecture only: normal USB webcam→Jetson Nano→USB serial→ESP32-S3→sensors/UI/future servo/pump; Web/App↔REST↔Jetson. AI runs on Jetson, S3 is final actuator authority. No alternate MCU/camera architecture or new product feature in this closeout.

**Current M4 RTC migration:** RTC hardware changed from planned DS3231 to available DS1302 during M4 physical bring-up. `diag_rtc` usesCLK GPIO16,DAT/IO GPIO17(bidirectional),CE/RST GPIO18. OLEDalone remainsI2CSDA8/SCL9; noRTC0x68expectation. `DS1302_BRINGUP.md` / `DS1302_MIGRATION_RESULT.md` supersede old RTC selection/testcounts without rewriting the earlier cutoff. **DS1302 SOFTWARE SUPPORT READY — PHYSICAL RTC VALIDATION NOT YET PERFORMED**.

Current migrationverification supersedes earliercutoffcountsbelow: actualfullrun2026-10-09T02:32:53.153670+00:00 **309Python/3451native(140+3311)/7vectors/46guards/18buildsPASS**,subsequentstatic/qualityPASS; `DS1302_MIGRATION_RESULT.md` holdsnewbundle/hash/size. Earlier309/3271/39handoffretainedashistorical.No source-output/RTCphysicalPASS inferred.

## Actual hardware context / boundaries

User-supplied observations: Nano2GB/Ubuntu18.04.6/L4T32.7.6/systemPython3.6.9,CUDA10.2/cuDNN8.2.1/TRT8.2.1.8/customOpenCV4.8,cuda count1; Generic Web Camera4a54:5233,/dev/video0,720pMJPG300frames/0fail/10.008s/29.97FPS; S3revv0.2,40MHz,16MBflash,**PSRAM NOT DETECTED**; bridge1a86:55d3/cdc_acm,/dev/ttyACM0,dialout/pyserial3.5; no-stubfactoryflash/reset/hashverified, initial PING100/GET_STATUS101 payload01/IDs/CRC PASS, unplug/re-enumerationPASS.

Post-reconnect protocol remains **USER-REPORTED PASS without stored raw transcript**; dates/imageSHA/numericalCRC/rawhex not supplied remain null in `evidence/M3_REAL_HARDWARE_FACTS.json`. Formal M3 closeout pending; M4 sensors/actuators NOT TESTED. Agent only executes host checks/build/packaging/dry plans, no Jetson flash/camera/sensor or OS install. No ownercat dataset/model trained;1080p advertised is not measured runtime.

## Exact deploy environments and guards

| Environment | Purpose |
| --- | --- |
| `esp32s3_16mb_no_psram_hw_safe_uart` |Binary frozenv1 HW_SAFE, all default physical pins unassigned |
| `diag_i2c` |First M4 empiricalbus scan, ASCII only |
| `diag_rtc` |DS1302three-wire16/17/18,BCD/date/CH/WP,explicitset+readback; nobootset |
| `diag_hx711` |Raw/readiness first; calibration separate |
| `diag_food_sensor` |FoodTRIG6/ECHO7 with mandatory3.3V conditioning/review |
| `diag_water_sensor` |WaterTRIG10/ECHO11; no pump, blind-zone/range review |
| `diag_oled_button_buzzer` |MinimalOLED/button intent; buzzer disabled until revieweddriver |

All seven use measured16MB/no-used-PSRAM bridge base,HW_SAFE,actuator/servo/pumpflags0,CDC/nativeUSB0. Sixdiagnostics inherit `m4_sensor_bringup`:sensor4..13 +DS1302CLK16/DAT17/CE18. Realprofiles have **no BOARD_HAS_PSRAM**, noqio_opiinheritance. LegacyN16R8/`*_surrogate` are regressiononly, not deploymenttargets. Normalpins/actuatorpinsremain-1.

`pins.h`:SERVO_PWM/PUMP_MOSFET=UNASSIGNED(-1), all normalpins-1; candidateM4actuator macros also-1. Globalgpio_verified=false. Future14/15 are documentation only. Compile guards reject PSRAM, conflictingUSB, SIMmix, wrongtarget mode/pin overrides or actuator enable. AI_SHADOW_MODE=true default, automaticphysicalfeeding false; frozenwire encoding/CRC/payloads/golden vectors unchanged. Diagnostic ASCII is not binaryUART v1.

## Final verification record

Prior adaptation baseline actually passed309 Python,140+3131=3271 native assertions,7 vectors,39 guards,18 safe builds. This final pre-quota run was executed again, not inferred. Logs `.checks/summary.json` and `.release/quality_summary.json` preserve actual output/environment.

**ACTUAL FINAL CLOSEOUT PASS:** `scripts/run_checks.ps1`, runner timestamp `2026-10-08T16:52:22.451794+00:00`, process success/PASSED_HOST_CHECKS. **309 Python passed /0 failed /0 skipped /0 errors;140 safety +3131 driver =3271 native assertions PASS;UART7/7;compile guards39/39;all18 safe builds PASS** (seven currentreal no-PSRAM environments plus11legacy/surrogate regressions). Dependency consistency/imports/dataset validation PASS; datasetDATASET_NOT_AVAILABLE. No new tests/code/profiles added in this closeout; counts unchanged.

Subsequent quality command `python scripts/run_quality_checks.py` actually PASS: Ruffcorrectness rules includingbringup, mypy5 selectedfiles, bothnative harnesses strictconversion/shadow/pedantic -Werror/run, frozenOpenAPI snapshot and internaldocs/source audit. Typecheck is selectedscope, not wholeproject; no browser rendering or physicalsensor test claimed. Full normal/native/build logs and quality/audit logs are retained; no failure hidden.

Actual host dry-run on existingdiag_i2cfactory430720B/hash receipt succeeded and reportedflashed=false. Same validarguments plus`--apply` **without** `--allow-factory-overwrite` returnedexit2/FLASH_ABORTED at consentgate **before port/esptool access**. This expectednegative check is not a regression failure or actual flash. Code path withoverridebutnoapply remainsDRY_RUN; factorywrite requiresbothflags. No Jetson command/install/deviceIO was performed byagent. Scripts themselves remainedunchanged.

Final second boundary check was also **executed**: `--allow-factory-overwrite` **without** `--apply` returnedDRY_RUN/flashedfalse, no port opened. After final documentation update, quality/source/docs checks PASS and release generator produced349 hashed entries including18 firmware images; `make_release_manifest.py --verify` PASS/no mismatches. Source/firmware manifests and all test/quality logs remain in ignored `.release/` / `.checks/`, not physicalsensor evidence.

Resolved PlatformIO configuration was inspected (not just raw source): all seven real targets have0 actuator/servo/pump flags, noPSRAM/nativeCDC, default_16MB partitions; sixM4modes1..6/candidateprofile1. Existing39guard cases and default/mapping staticasserts enforce these. No application/firmware/config/test changes are needed by this freeze audit; only documentation/result metadata is finalized.

## Before changing binary firmware: preserve M3 reconnect receipt

If needed, while the currently flashed image is HW_SAFE **binary**, close serialmonitors and from `jetson/` run:

```sh
python3 -m bringup.devices
python3 -m bringup.serial_probe --device /dev/ttyACM0 --count 3 --save ../evidence/serial/UNIQUE_connected.json
```

Use a timestamped UNIQUE name. Physically unplug→node disappears→oldnodeprobeFAIL; reconnect→enumerate actualnode→newreconnected probe withrawTX/RX/matchedID/CRC. No FEED_REQUEST is sent. Do not run binaryprobe against ASCII sensor firmware or fabricate missingreceipt from expectedframes.

## Exact FIRST M4 procedure — I2C ONLY

### A. Wiring (power OFF first)

Leave RTC/HX711/ultrasonic/button/buzzer/servo/pump disconnected. Firstscanuses **ONLY compatible OLED I2C**, notDS1302. NoDS3231installed/expected. RTCis a separate three-wire step below.

```text
ESP32-S3 3V3 → module VCC ONLY if its actual module is3.3V-compatible
ESP32-S3 GND → module GND (common GND)
ESP32-S3 GPIO8 → module SDA
ESP32-S3 GPIO9 → module SCL
```

Confirm actual headerlabels/OLEDpinorder/3.3Vcompatibility/pull-ups. If module needs5V, STOPforlevels/supplyreview; neverfeed5VGPIO. Candidatepins are notphysicalPASS. DS1302module/battery review and wiring occurseparately withpowerOFF, not onSDA/SCL.

### B. Build/package on Windows (project root)

```powershell
& .\scripts\build_esp32_windows.ps1 -EnvName diag_i2c
```

No flash. Builder prints a **new** `.deploy/diag_i2c_TIMESTAMP` folder with bootloader.bin,partitions.bin,boot_app0.bin,firmware.bin,firmware.factory.bin and deploy_manifest.json. Record profile/source/hash and use the exact factorySHA from that currentmanifest, never an earlier hardcodedhash after rebuild.

### C. Transfer bundle + required source

On Jetson create a reviewed destination: `mkdir -p "$HOME/for_cat_firmware"`. Windows:

```powershell
scp -r ".deploy/ACTUAL_BUNDLE" USER@ACTUAL_JETSON_IP:~/for_cat_firmware/
```

USER/IP/ACTUAL_BUNDLE are placeholders. Jetson project must already have current `scripts/flash_esp32_from_jetson.sh`, `jetson/bringup/`, root `ai/{__init__,sampling,label_schema}.py`. Transfer source only, not Windows venv/caches/private data. On Jetson verify `sha256sum "$HOME/for_cat_firmware/ACTUAL_BUNDLE/firmware.factory.bin"` against manifest; no install/upgrade is required here.

### D. Jetson DRY-RUN (project root, current systemPython)

```sh
sh scripts/flash_esp32_from_jetson.sh --profile diag_i2c --port /dev/ttyACM0 --image "$HOME/for_cat_firmware/ACTUAL_BUNDLE/firmware.factory.bin" --sha256 ACTUAL_FACTORY_SHA256
```

Default dry-run validates image/header/hash/profile and prints commands; **opens no port and writes noflash**. Use actual enumerated node if replug changed it. Closeminiterm/probes before applying. Review/backup existingNVS/safety/calibration if present: factory covers0x0..image sectors, includingNVS/gaps; does not mean “app-only”.

### E. Apply ONLY explicitly after range review

```sh
sh scripts/flash_esp32_from_jetson.sh --profile diag_i2c --port /dev/ttyACM0 --image "$HOME/for_cat_firmware/ACTUAL_BUNDLE/firmware.factory.bin" --sha256 ACTUAL_FACTORY_SHA256 --apply --allow-factory-overwrite
```

Factorywriting is blocked without **both** flags. Helper uses system `python3 -m esptool --chip esp32s3 --port NODE --baud 115200 --no-stub` for ROMflash_id(required16MB), `write_flash 0x0 FILE` and `verify_flash 0x0 FILE`. No stub fallback/erase-all. A verify-only action (`--verify-only --apply`) performs no write. Application-only updates at0x10000 require already matcheddefault_16MBbootloader/partitions and usefirmware.bin/hash; they preserveNVS, not justify guessing a layout.

### F. Empirical scan, output and STOP

```sh
python3 -m serial.tools.miniterm /dev/ttyACM0 115200
```

Banner must saydiag_i2c/HW_SAFE/output0/candidatepins/PSRAMnotused/ASCII. Startupscanonce; `scan`,`status`,`help` remain. OLEDcandidate **0x3C**, somevariants0x3D, must empiricallyACK. **No0x68RTCexpectation: DS1302 is notI2C.** Missing0x68 is notRTCfailure. Unexpected/missingOLEDaddress/unstablebus→reviewactualwiring/module/power, notautopass.

Expected format, **NOT observed output**:

```text
I2C_ACK address=0x3C identity NOT_VERIFIED
I2C_SCAN_COMPLETE probes=112 responding=N result=RESPONSES_OBSERVED ...
```

With no ACK: responding0/NOT_CONNECTED is truthful, notPASS. ACK establishes respondingaddress, not moduleidentity/RTCtime/OLEDdisplay correctness. STOP on abnormal voltage/pull-ups/wiring/address, wrongprofile/SIM/outputflags/hash/chip/flash/partition/node, unstablepower/serialcorruption or unexpectedmotion. Save actualerror, do notswitchstub/enablePSRAM/forceGPIO.

Close terminalCtrl+]. Keep photos/module/wiring/voltage/source/imagehash,date/time and rawscanlog with expected-vs-actual result. Nextseparatemodes: RTC→HX711→food→water→UI per `REAL_HARDWARE_NEXT_STEPS.md`; echodivider/buzzerreview gatesremain. Servo/pump are not enabled anywhere in this workflow.

### G. Current RTC step — DS1302, NOT I2C

PowerOFFrewire: S33V3→moduleVCC(ifcompatible),GNDcommon,GPIO16→CLK,GPIO17→DAT/IO,GPIO18→RST/CE. Actualheaderorder/labels/battery mustbeverified. OLEDstays8/9separately. Windows `build_esp32_windows.ps1 -EnvName diag_rtc`; transfernewbundle/hash and use same no-stubwrapper `--profile diag_rtc` with its actual factoryfile/hash (explicitapply+factoryoverride afterrange/NVSreview), or already-matchedpartition application-onlyfirmware.bin/hash.

ASCII115200banner identifiesDS1302/16/17/18/BOOTREADONLY. JSONonce/sec reportsHEALTHY/NOT_CONNECTED/INVALID_TIME/CLOCK_HALTED/IO_ERROR and validYYYY-MM-DD HH:MM:SSUTCelseNULL. `set-utc ACTUAL_YYYY-MM-DDTHH:MM:SSZ CONFIRM` is the **only** setpath;CHcleared,WPtemporarilycleared/restored,validactualreadbackprinted. Noautobuildtime/charger/DS3231OSFbehavior; DS1302year2000–2099. See `DS1302_BRINGUP.md`; physicalRTCvalidation NOT PERFORMED.

## Blockers and continuation after quota

- Sensor/pin/voltage/RTC/NVS/accuracy/UI/actuator evidence NOT PERFORMED; noM4PASS. Stored reconnectreceipt/date/imagehash stillneeded for formalM3closeout.
- Full modernbackend cannotrun system3.6; preserve workingcustomOpenCV/CUDA/TRT and follow `JETSON_NANO_RUNTIME_COMPATIBILITY.md`. Lowutilities are3.6syntax/stdlib audited and hostfake-tested, not agent-executedonNano.
- Jetson PlatformIO pinnedlinux_aarch64 resolution unsupported; buildWindows,transfer,ROMno-stubflash. Do notinstallanything onJetson toforceit duringthishandoff.
- NoOWNERcorpus/trainedmodel/productionthreshold; publicprovenancebootstrapdoesnotreplace owncat/camera finaltest. AIshadowtrue/noautomaticphysicalfeed.

Give ChatGPT this file plus exact nonpersonaloutputs,board/module/wiringphotos and `TOMORROW_NO_OPENCODE_CHECKLIST.md`. Existing detailedworkflow `WINDOWS_BUILD_JETSON_FLASH.md` agrees withactualscripts; placeholdersmustbereplacedwithobservedvalues. No routine software expansion needed. **Freeze this handoff and proceed only with actual hardware/data evidence.**

## Closeout file changes / final freeze

This pass added `FINAL_OPENCODE_HANDOFF.md` and clarified **I2C-only first step** in `REAL_HARDWARE_NEXT_STEPS.md`, `TOMORROW_NO_OPENCODE_CHECKLIST.md`, `WINDOWS_BUILD_JETSON_FLASH.md`. Working architecture/application/firmware/scripts/protocol/tests/gates were not modified. Generated `.checks/` / `.release/` verification and source/18-firmware hash manifests are ignored release evidence, not new physical results. Final link/hash verification is rerun after this result update so source checksums describe the final handoff text.

**M4 SOFTWARE READY, PHYSICAL SENSOR VALIDATION NOT YET PERFORMED** — frozen at the current software/evidence boundaries. No new hardware PASS or automaticmilestone award.
