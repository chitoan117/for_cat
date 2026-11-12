# Real-hardware adaptation — executed host result and physical provenance

Current stage: actual reported M3 core communication/webcam/chip observations, reconnect evidence closeout pending, **M4 sensors/actuators NOT TESTED**. No automatic full milestone award. Architecture unchanged: normal USB webcam→Nano→USB serial→S3 measured16MB/no-used-PSRAM→peripherals/future actuators, Web/App↔REST↔Nano. gpio_verified remainsfalse, production/actuator pins-1, all actuator flags0, AI shadowtrue.

## Before changes / preserved user work

Stored pre-change host baseline301 Python,3271 native,7 vectors,18 guards,11 builds PASS; the manually appended no-PSRAM environment really existed. Refactored it in place with its original name, kept five legacy profiles and six explicitly named surrogate diagnostics. Default normal pins remain unassigned; explicitM4candidate mode4..13 is separate. See `REAL_HARDWARE_REPOSITORY_AUDIT.md`.

## Actual executed Windows results

Full `scripts/run_checks.ps1` succeeded at runner timestamp **2026-10-08T16:14:48.327150+00:00** (`.checks/summary.json`), not inferred from earlier numbers:

| Check | Result |
| --- | --- |
| Python | **309 passed,0 failed,0 skipped,0 errors**;8 new risk/compatibility tests, earlier tests retained |
| Native safety/drivers | **140+3131=3271 assertions PASS**, unchanged count |
| UART | **7/7 frozen vectors PASS**, portable3.6 codec also cross-tested |
| Compile guards | **39/39 PASS**, original18 retained;21 added measured/candidate/actuator/PSRAM/USB cases |
| Safe builds | **18/18 PASS**:5 legacysafe +1 real-safe +6 candidate diagnostics +6 legacydiagnostics |
| Imports/dependency consistency | PASS on host, no device/model starts |
| Dataset | DATASET_NOT_AVAILABLE,0 repository real samples |
| Windows deploy builder | Executed successfully fordiag_i2c, five products+JSON hash receipt in ignored `.deploy/` |
| Jetson flash/new utility physical IO | **NOT RUN BY AGENT**; host plans/grammar/fakeI/O only |

Subsequent developer quality checks actually PASS: Ruff including newbringup package, mypy5 selected sourcefiles, strict native -Werror harnesses, frozen OpenAPI contract and source/docs audit. First audit failed only because this result page had not yet been created; after creating it links/refs PASS, no failure suppressed. No actual Python3.6 interpreter, hardware-only sensor test or shell-flash execution on Jetson is claimed by host grammar checks.

Latest executed `build_esp32_windows.ps1 -EnvName diag_i2c` produced `.deploy/diag_i2c_20261008T162758Z`: factory430720B SHA256`dc81140a70b8388f476e50cfe88b0aa5f744b64af891f4e6194fb6523b4d005c`; app365184B SHA256`2f290ffe7f7541e92438de8b27bf26cab5019965422062c6ce7cd7ed2109cb89`. Bootloader/partitions/boot_app0 sizes/hashes in deploy manifest. Actual host `bringup.flash` DRY_RUN validated thisfactory/hash/profile/no-stub plan, opened noport and flashedfalse. Use newly printed receipt if rebuilt; don't reuse these hashes blindly for a changedimage.

Initial build failed because a new guard interpreted sharedSDK CONFIG_SPIRAM_USE_MALLOC capability as board enable. Fixed that root cause; BOARD_HAS_PSRAM/explicit enable/SIM/USB/actuator restrictions remain hard. Real HW_SAFE anddiag_i2c then built PASS before full18-target regression. PlatformIO automatically updated isolated Windows SCons to4.41101.0; no Jetson package/OS change.

| Current real profile | RAM B /327680 | App flash B /6553600 | Host build |
| --- | ---: | ---: | --- |
| esp32s3_16mb_no_psram_hw_safe_uart |23704 |325513 |PASS |
| diag_i2c |25584 |358418 |PASS |
| diag_rtc |25568 |377422 |PASS |
| diag_hx711 |25576 |378866 |PASS |
| diag_food_sensor |25592 |377766 |PASS |
| diag_water_sensor |25592 |378194 |PASS |
| diag_oled_button_buzzer |25568 |360146 |PASS |

These are actual host footprints, not measured board RAM/PSRAM/sensor performance. Original flashed397312B image observation remains distinct from new diagnostic image sizes/hashes. Windows builder creates fresh immutable bundles; no flash in this pass.

## Changes by file/module

- Platform/safety: `esp32/platformio.ini`, `board_config.h`, `build_info.h`, `m4/{candidate_sensor_pins,diagnostic_config,arduino_io}.h`, `src/diagnostics.cpp`. HumanASCII only, candidate maps, bounded scan completion, explicit echo/buzzer review, measured-range command; no binaryv1 change.
- Capture: `app/camera/{settings,usb_webcam}.py`, `app/config.py`, `.env.example`;720pMJPG30 request/FourCC-before-size, bounded retries/backoff/reset and actual metadata. Mock remainsdefault, stale/queue1 pipeline preserved.
- Compatible bring-up: `jetson/bringup/{protocol,serial_probe,devices,camera,flash}.py`, init; dependency-free shared `ai/{sampling,label_schema}.py`, modern session/capture CLI metadata additions. Syntax/stdlib chosenfor3.6; actual3.6 execution here NOT RUN.
- Deploy: `scripts/build_esp32_windows.ps1`, `prepare_esp32_deploy.py`, `flash_esp32_from_jetson.sh`; checked hashes/type/profiles, dry-run default, no-stub115200 ROM16MB check, explicitfactory covered-range consent, application-onlyNVS-preserving option.
- Data/provenance: `ai/public_data.py`, `scripts/public_provenance.py`, capture/session/sampling and reviewed instructions; no download/model/train/owner labels from publicdata.
- Verification: guard cases, check_release18 targets, updated target-count assertion, `test_real_hardware_adaptation.py`; no weakened failure expectation. Camera/probe/capture tests usefake/syntheticfixtures.
- Evidence/docs: currentstate/architecture/README/chronology and new runtime/pin/deploy/M3/nextsteps/manual checklist; `docs/evidence/M3_REAL_HARDWARE_FACTS.json` is attributed user facts with missing raw/date/hash fieldsnull, MAComitted.

## Blockers and readiness

**Ready for intentional sensor-only bring-up** using supplied candidate pins after actual module/pull-up/ECHO/current/power review, not M4PASS. Startdiag_i2c, thenRTC,HX711,independentlevels,UI. Echo/buzzerstartup blocked until explicit acknowledgments; software1..400 range is not a calibrated blind zone. Sensor GPIOs are test-targets, not globally verifiedmapping; servo14/pump15 never assigned or enabled.

Full API/runtime on Nano system3.6 is BLOCKED: modern syntax/FastAPI/Pydantic/ARMwheels and GPUABI. Recommend isolatedmodernAPI plus preserved3.6capture/GPUboundary; full IPC/executor notimplemented/validated. Windows PIObuild is current supported path; Jetson PIO resolution failure not forced. New deploy/scripts physically NOT RUN on Jetson by agent.

User-reported initial M3 PING/GET_STATUS/CRC/ID/node disappearance/re-enumeration and camera test are incorporated faithfully; post-reconnectprotocol onlyUSER_REPORTED_PASS. Save actual dated reconnect raw probe/imageSHA to formally closegate; no fabricated checksum/framelog. Ownercat corpus absent, AI untrained/publicsources notselected, shadowtrue.

Exact next physical action and STOP/wiring/commands: `REAL_HARDWARE_NEXT_STEPS.md`; quota-independent checklist: `TOMORROW_NO_OPENCODE_CHECKLIST.md`. No model/hardware result is upgraded from compilation or test-target acknowledgment.
