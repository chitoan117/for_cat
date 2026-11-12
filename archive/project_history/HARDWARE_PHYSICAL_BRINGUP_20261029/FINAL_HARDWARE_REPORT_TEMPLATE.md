# FOR_CAT — physical session report (owner + ChatGPT review)

Date/time/timezone: ___; observer: ___; testscope: ___
BackupA/Bđãcomplete: PASS_OWNER_CONFIRMED + directreadonlyfilehash; khônglượt3/oldLASTEXITCODE.
A/Bmỗi16777216bytes, SHA56a04d58bd8063e64f6b043a6b91d2d412c64d75e563ee58d81a83666d9a8e16.
Acceptedpairreceipt: `web_hardware/accepted_backup_pair.json`; originalfileskhôngsửa.
Two-passreceipt / oldprobe-mapcomparison / mismatchnotes: ___
Actualpartitiontable / bootloader-appintegrity / OTACRCcopies/states: ___
Actualrunningpartitionlog + backupboundreview / rollbackextractSHA: ___
APP-only authorization: NO until allbackup/boot/electricalgates reviewed.
Board/USBID/ROMchip/flashID: ___; port/baud: ___; UART0routeverified: ___
PSRAM8MB esptoolreport: ___; firmwarePSRAMworking: NOT_VERIFIED, keepNoVerifiedPSRAM.
Firmwareprofile/KITid/appSHA256/flashedoffset: ___
Fullbackup path/hash/layout/confirmedactivebank: ___
CalibrationRAMstatus BEFORE reset savedat: ___; RAMloss acknowledged: ___
Bridge scope/originalstate/capturefinallyrestoration/status: ___
Powerisolation/5Vsupplies/commonGND/photos: ___
Echolevelshifter/divider/peakmeasurement evidence: ___ (CONFIRM is NOT proof)
ECHO13___V/file___; ECHO17___V/file___; ECHO15___V/file___; ECHO10___V/file___
Sensorcriteria frozenBEFORE: referencegeometry/range/error/spread/validfraction___
Eachpoint3repeatwindows/logtimestamps and expected vsactualworksheet: ___

| Component | Config / testpoints | Rawlog / timestamps | USER_OBSERVED physical evidence | Result/reviewer |
|---|---|---|---|---|
|HC1 GPIO12/13|40→15→40; loss/reflection; multiplex|___|thước/ảnh/trace___|NOT_VERIFIED|
|HC2 GPIO16/17|___|___|___|NOT_VERIFIED|
|JSN1 GPIO14/15|module revision/blindzone/≥safe distance___|___|___|NOT_VERIFIED|
|JSN2 GPIO18/10|___|___|___|NOT_VERIFIED|
|PIR GPIO11|warmup,noise,hold,retrigger___|___|motionphysicaltime___|NOT_VERIFIED|
|Buzzer GPIO2|ACTIVE_LOWreview,defaultOFF,2pulses,timing,STOP___|___|audio/scope___|NOT_VERIFIED|
|Servo GPIO6|unloaded,pulses,ARMmovement,timeout,STOP___|___|video/current/closurelimit___|NOT_VERIFIED|
|Pump GPIO7|inert; measuredOFF/bootbias; conditionalimage/priming/shortpulse___|___|meter/flow/video/current___|NOT_VERIFIED|
|HX711 static GPIO4/5|Existing5/10/20/35g, latest35g→34.981g|`HX711_ACCEPTANCE.json`|Owner chấpnhận sai số0.019g≈0.054%; không retest|PASS_STATIC_ACCEPTED|

HXexisting5/10/20/35g: ACCEPTED_STATIC_PHYSICAL, không đo lại; latestfull30srawattachment: ___
ActualALL109samplemin/max/range/sigma iffullfileexists: ___; otherwise NOT_AVAILABLE.
NVS/rebootpersistence: NOT_VERIFIED; closed-loopservo35g: NOT_VERIFIED; currentRAMafterreset: UNKNOWN.
Không yêu cầu5/10/20/35/38g lại để giảmerror; integrationcontextverification riêng nếuđượcyêu cầu.
OLED priorownerdisplayevidence: ___ (khôngyêucầuauto-retest); buttonactiveLOWblockedrequest: ___

DiagnosticUARTopened: ___; serialconnected: ___; bridgevalidtelemetrycount/mode: ___
Firmwaremode compatibility != sensoraccuracy != physicalPASS. HX711_REFERENCE may
still yieldzero acceptedframes in currentbridge; do not widenparser to claimPASS.

Unexpectedmotion/sound/pump-on/reset/brownout/timeout/invalid/crosstalk: ___
ImmediateSTOP/disconnectactions: ___; finalexternalpower/loadstate: ___
Rawunfilteredfiles/hash, sensorreferencepositions and allfailedpoints retained: ___
SoftwareACK receipt: ___ (**NOT** FEED_SUCCESS/current/flow/acoustic/closure proof)
Reviewdecision and exactscope/remainingblocks: ___

```text
FOUR_ULTRASONIC_PHYSICAL_PASS=NOT_VERIFIED
PIR_PHYSICAL_PASS=NOT_VERIFIED
BUZZER_PHYSICAL_PASS=NOT_VERIFIED
SERVO_PHYSICAL_PASS=NOT_VERIFIED
PUMP_PHYSICAL_PASS=NOT_VERIFIED
ESP32_TELEMETRY_PASS=NOT_VERIFIED
HX711_PHYSICAL_STATIC_TEST=PASS
HX711_STATIC_MEASUREMENT_PHYSICAL_PASS=YES
HX711_35G_REFERENCE_MEASUREMENT=PASS
HX711_MEASUREMENT_ACCURACY_ACCEPTED=YES
HX711_RETEST_REQUIRED=NO
HX711_CALIBRATION_PERSISTENCE=NOT_VERIFIED
HX711_CLOSED_LOOP_DISPENSE_35G=NOT_VERIFIED
BACKUP_A_COMPLETION=PASS_OWNER_CONFIRMED
BACKUP_A_B_CONSISTENCY=PASS_FILE_INTEGRITY
ACTUAL_RUNNING_BOOT_BANK=NOT_VERIFIED
FLASH_AUTHORIZED=NO
PRODUCTION_SERVO_LOCK=LOCKED
PRODUCTION_PUMP_LOCK=LOCKED
```

HXstaticacceptance trên làquyếtđịnhowner cóevidence; không dùng genericpending đểphủnhận nó.
Only human-supervised review with actual evidence can amend other results, not firmware
output, toolcapturecompletion, buildPASS or simulatedtests. Fullfeed35g/flow/AI
production integration remains a separate acceptance scope.
