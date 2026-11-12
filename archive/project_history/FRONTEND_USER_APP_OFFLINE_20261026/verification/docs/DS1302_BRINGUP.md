# CURRENT RTC DS1302 — software integrated, physical validation pending

**RTC hardware changed from planned DS3231 to available DS1302 during M4 physical bring-up.** Canonical `diag_rtc` now uses DS1302, not a temporary demo or I2C RTC. Higher-level snapshot/health/DateTime/UTCepoch/day and invalid-RTC feed rejection remain generic; native historicalDS3231 support/tests are retained only as compatibility/regression evidence.

## Wiring — power OFF before rewiring

| ESP32-S3 | Actual DS1302 module signal |
| --- | --- |
| 3V3 | VCC/main supply, verify actual module labels |
| GND | GND common |
| GPIO16 | CLK/SCLK |
| GPIO17 | DAT/IO **bidirectional**, not permanently driven output |
| GPIO18 | RST/CE activeHIGH |

OLED remains I2C SDA8/SCL9,3.3V-compatible supply/pull-ups/commonGND. DS1302 is **NOT I2C** and must not be wired to SDA/SCL or expected at0x68. Module header ordering varies: use actual labels, not photo order/color. Keep logic/main supply3.3V for currentS3, review backup battery/module circuits separately. Driver never writes charger register or assumes battery type. Servo/pump14/15 remain candidate-only/-1/disabled and electrically disconnected.

## Verified protocol/design source

Manufacturer [ADI/Maxim DS1302 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ds1302.pdf), Rev3/15: command formatp5, CE/input/output/buffersp6, CH/WPp7, burstp8, registertablep9, timingpp11–12. Public PDF text was retrieved through a reader after direct fetch returned binary; no device result follows from reading a datasheet.

- Commands match datasheet: seconds80/81,minutes82/83,hours84/85,date86/87,month88/89,weekday8A/8B,year8C/8D,control8E/8F,clockburstBE/BF (write/read hex).
- CEHIGH throughout transaction, CLKLOW atCErise, bitsLSB-first. Inputs latch on rising; output starts on **first falling after finalcommandbit**. Host switches DAT toinput while finalcommandCLK isHIGH, before falling, then samples stableLOW and staysinput through reception/CErelease.
- Clockburst reads coherent secondarybuffer8bytes inDS1302order seconds/minutes/hours/date/month/weekday/year/control. All8bytes are written for explicitburstset; commits onCEfall. Short4µspauses meet slow2Vsetup/inactive/clock minima; fixedbyte loops, no readiness wait or longdelay. ESPGPIO timing/accuracy still needs real measurement.
- CH is secondsbit7; WP controlbit7; hoursmodebit7/PMbit5; noDS3231OSF/statusregister/century behavior. Canonical century convention is **2000–2099**; writes outside that range rejected rather than wrapped. Existing generic calendar stays Gregorian; February/leap/ranges/reservedbits are validated.
- Normalbegin/poll do not modify clock/CH/WP/charger. Explicitset clearsWP, verifies writablecontrol, writesCH0/24h/timeburst, restores priorWP and readsback. Readback must be valid and matchrequestedUTCwithin0–1s tick; failure leaves time absent/unsafe. No compiler time fallback.

DS1302 has no electricalACK. All-zero/all-one read returns NOT_CONNECTED/NO_RESPONSE heuristic, which can also indicate uninitialized/disconnected/stuck bus—not independent proof of absence. PlausibleBCD alone cannot certify battery retention/drift/wiring or a spoofed/stuck plausible value; physical reference/fault/reboot tests remain required.

## Windows build → explicit Jetson deploy

```powershell
# Project root; packages the ACTUAL new hash/size
& .\scripts\build_esp32_windows.ps1 -EnvName diag_rtc
# Compile only: .\.tools-venv\Scripts\pio.exe run --project-dir esp32 -e diag_rtc
```

Transfer printed `.deploy/diag_rtc_ACTUAL_TIMESTAMP` bundle/manifest. From Jetsonprojectroot use systemPython/esptool3.3.3 through wrapper:

```sh
sh scripts/flash_esp32_from_jetson.sh --profile diag_rtc --port /dev/ttyACM0 --image "$HOME/for_cat_firmware/ACTUAL_RTC_BUNDLE/firmware.factory.bin" --sha256 ACTUAL_FACTORY_SHA256
# Dry-run; after covered-range/NVS review add --apply --allow-factory-overwrite.
```

Always--no-stub/115200/ROMflash16MBpreflight, nevererase-all. With already matcheddefault_16MBbootloader/partitions, preserveNVS when changing diagnostic by firmware.bin/hash with `--application-only --apply` at0x10000. Use a new actualmanifest, not pre-migration hashes. No Jetsoninstall/Python/GPUchange is part of this migration.

## Diagnostic commands/output — examples, NOT observed results

```sh
python3 -m serial.tools.miniterm /dev/ttyACM0 115200
```

Banner includes `mode=diag_rtc`,HW_SAFE,actuator/servo/pump0 and `RTC=DS1302 CLK=16 DAT/IO=17 CE/RST=18; 3-WIRE NOT I2C; BOOT READ ONLY; UTC2000-2099`. Normal JSONreport once/sec includes rtc_typeDS1302,rtc_health,rtc_result,rtc_reason,rtc_epoch and valid `rtc_utc` asYYYY-MM-DD HH:MM:SS, otherwise null.

Possible rtc_result: HEALTHY,NOT_CONNECTED,INVALID_TIME,CLOCK_HALTED,IO_ERROR (NOT_CONFIGURED if pins inactive). Underlying reason identifies NO_RESPONSE/WRITE_PROTECTED/READBACK_MISMATCH. Driver health is software observation, **not RTC accuracy PASS**. `status` requestscurrentreport; `help` listscommands. No automaticset atboot.

If time halted/invalid, obtain an independently knownactualUTCreference, e.g. `date -u` only if Jetsonclock itself is validated; then explicitly:

```text
set-utc ACTUAL_YYYY-MM-DDTHH:MM:SSZ CONFIRM
```

Successfulcommand prints `RTC_DS1302_EXPLICIT_SET READBACK_VALID UTC...` and actualreadbackreport. Rejection prints result/reason and no usabletime. Stop on wrongflags/pins/supply/modulelabels, unexpectedreads/IO/WP/readbackfail; do not retry by enablingactuators/charger/PSRAM or forcingbuildtime.

Record actualcommand/UTCreference/timezone,profile/source/imagehash,wiring/photo/modulebattery,powercycle/retention/rollover/drift/CH/WPfaults and PASS/FAILagainststatedcriteria. Physical RTC was NOT testedbyagent. **DS1302 SOFTWARE SUPPORT READY — PHYSICAL RTC VALIDATION NOT YET PERFORMED**.
