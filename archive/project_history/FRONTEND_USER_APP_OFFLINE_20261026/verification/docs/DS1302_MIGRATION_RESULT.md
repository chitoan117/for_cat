# DS1302 migration — software integration / verification record

**RTC hardware changed from planned DS3231 to available DS1302 during M4 physical bring-up.** CurrentcanonicalRTCDS1302GPIO16CLK/17bidirectionalDAT/18CE,OLEDI2Conly8/9. User ownsDS1302; no actual RTCtime/readback/retention/wiringresult was supplied or executedbyagent. No M4/RTCphysicalPASS.

## Inspected before editing

`rtc.h` held genericDateTime/calendar/BCD/epoch and legacyDS3231I2Cdriver; `diagnostics.cpp`createdDs3231(bus),mode2Wire.begin/read/set; snapshot mappedhealth/time to genericRTCvalid/day/epoch. Interfaces hadDs3231Clock/epoch names; all normalpins-1; candidate4..13/output0;18safe profiles/noPSRAMcurrentboard. Existingnative testscoveredDS3231/faults/calendar. All higherlevelsafety policy and frozenUART remain unchanged.

## Implemented migration

- Generic `RtcClock` / `RtcEpochSeconds`, backwardcompatibilityDs3231aliases; historicaldriver/tests retained,notcurrentselection.
- Internal `m4/ds1302.h`: datasheet-verified commands/LSB/CE/turnaround, coherent8-byteburst, validatedBCD/calendar/12h/24h/year2000–2099/CH/WP, explicitsetonly withWPclear/verify/restore/readback0–1s tolerance. No charger/RAM/statusregister writes and no boot/compiler clockset. Boundedshort4µs timing/fixedloops,PinIO injection,defaultunassignedconfigtouchesnoGPIO.
- Default `pins.h`addsRTC_CLK/DAT/CEall-1; candidateconfigdefines16/17/18onlyindeliberateM4profile. Uniqueness/range/reservedguards include sensor/I2C/14/15/19/20/38/43/44, sevenbadRTCoverride cases preserve prior39guard tests.
- `diag_rtc`nowinstantiatesDs1302(pins_io),noI2Cbegininmode2. BootRTC/pin/readonlyinfo,JSONonce/secvalidYYYY-MM-DD HH:MM:SSUTC/epoch ornull,resultHEALTHY/NOT_CONNECTED/INVALID_TIME/CLOCK_HALTED/IO_ERROR/reason. Existingexplicitsetcommand migratesDS1302andprintsverifiedactualreadback; snapshot refreshedonset/rejection.
- `diag_i2c`continuesactualACKscanforOLED/futureperipherals,notRTC; no required0x68. NormalHW_SAFEstilldoesnotoperationallyfeed or collect newproductiontelemetry.

## Tests / executed evidence

Targeted strictnative `-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Werror` executedPASS with **3311 driver assertions**, preserving3131old andadding180meaningfulDS1302checks. Hardware-emulatingfakePinIOlatchesonrising/drivesonfalling, verifieshostinputBEFORElastcommandfall/LSB/idleCE/CLK/nocharger/WP/burst/coherentreadback/invaliddates/CH/disconnected/stuckwrites and genericRTC_INVALIDfeedrejection. ExistingDS3231checksnotremoved/weakened.

TargetedWindows `pio run -e diag_rtc -e diag_i2c` bothbuildPASS; noPSRAM/nativeCDC/actuatorenable. Full finalverification/all18builds/guards/staticresults are recorded after actualcompletecommand execution below, not extrapolated from targetedpass.

**ACTUAL FULL RUN PASS:** `scripts/run_checks.ps1`, runner timestamp **2026-10-09T02:32:53.153670+00:00**, PASSED_HOST_CHECKS. **309 Python passed/0failed/0skipped/0errors;140safety+3311driver=3451nativeassertionsPASS;UART7/7PASS;compileguards46/46PASS;safeprofiles18/18BUILDPASS**. Existing39guards retained plus7badRTCoverridecases; noPythoncountinflation. Dependency/import/datasetchecksPASS,ownerDATASET_NOT_AVAILABLE. SubsequentRuff/mypy5selectedfiles/strictnativebothharnesses/OpenAPI/source-docsauditPASS. Logs `.checks/` / `.release/`,notphysicalRTC evidence.

Windowsbuilder `build_esp32_windows.ps1 -EnvName diag_rtc` actuallyexecutedPASS/package at `.deploy/diag_rtc_20261009T024930Z`: app385952B SHA256`9bdbb5406bd5a360ffed88fbcbb4b5b47576ceee69091b2d235dfd6952e03ae7`; factory451488B SHA256`a8a449587e4bde7f5d8d9fd60f8b94bfd64251d53599730b574c362d5a3bd5fe`. RAM25600B/327680,appflash378966B/6553600. Source/profile or future rebuild maychangehash; use actualnewmanifest. NoJetsonflash/hardwaretest orpackageinstallperformed.

Actualhost `bringup.flash --profile diag_rtc` dry-run validated thatfactoryfile/hash and no-stubflash_id/write0x0/verifyplan; returnedDRY_RUN/flashedfalse and openednoport. Source/18firmwarehashmanifest is refreshed/verified after finalrecord updates; this is release evidence,notRTCphysicalvalidation.

## Files and remaining DS3231 references

Sourcechanges: `hardware_interfaces.h`, `sensor_drivers.h`, `m4/{rtc,ds1302,health,io,candidate_sensor_pins,diagnostic_config}.h`, `pins.h`, `src/diagnostics.cpp`, platformioRTCcomment; native harness +`ds1302_tests.h`, guardcases. Currentreadme/state/architecture/pin/BOM/voltage/time/RTC/I2C/handoff/thesisinstructions migrated; `DS1302_BRINGUP.md` iscurrentwiring/protocol/deployguide.

DS3231remains only in explicitlegacyimplementation/compatibilityaliases, legacyfake-busnative regressions/genericold-format helpers, and labelledhistoricalplannedcheckpointdocs. `DS3231_BRINGUP.md`isNOTcurrent; initialM3factsJSONisnotrewritten asifRTCselectionwasalwaysDS1302. No0x68responding-deviceexample is treatedascurrentRTCproof. Docsmentionselectionchangeforchronology,notclaimactualtestedDS1302.

## Deploy / unresolved blockers

Windowsroot `& .\scripts\build_esp32_windows.ps1 -EnvName diag_rtc`; newactualbundle/hash required. Jetsonroot `sh scripts/flash_esp32_from_jetson.sh --profile diag_rtc --port /dev/ttyACM0 --image ACTUAL_FACTORY_FILE --sha256 ACTUAL_FACTORY_SHA256`dry-run;applyrequiresboth`--apply --allow-factory-overwrite`. Already-matchedbootloader/default16MBpartitions mayusefirmware.bin/hash+application-onlyat0x10000preservingNVS. Always--no-stub; no agentflash/install/systemPythonchange.

Mainblocker isphysicalmodulelabel/supply/battery/CLK/DAT/CE/timing/reference/CH/WP/readback/retention/driftvalidation. DS1302hasnoACK:all0/all1readsareunreadableheuristic,notabsenceproof; plausibledatealonecannotcertifyaccuracy. Genericvalidityandclosed-outputgatesremainnecessary; noautomatedmilestoneaward. See `DS1302_BRINGUP.md`forSTOP/wiring/terminaloutput/evidence.

**DS1302 SOFTWARE SUPPORT READY — PHYSICAL RTC VALIDATION NOT YET PERFORMED**
