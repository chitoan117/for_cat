# M3 / M4 physical gates — reported core evidence, closeout pending

Actual user-supplied M3 chip/flash/webcam/initial USB protocol/CRC/ID/unplug/re-enumeration PASS scopes are in `M3_PHYSICAL_VALIDATION_RECORD.md`. Post-reconnect protocol is user-reported PASS; exact raw/date/image reference remains pending, so formal closeout is not automatically awarded. Gate criteria below are preserved; current work is M4 sensor-only preparation, not M4 PASS. No servo/pump enable.

No completion score changes and no gate is declared passed by this pack. Tests/builds/simulators and filled templates without actual hardware observations do not qualify.

## Exact M2 → M3 minimum

All must have real dated physical evidence:
1. Identified real Jetson boots/runs (model/power/environment recorded).
2. Identified real ESP32/S3 runs the reviewed **HW_SAFE, simulation=0, actuator=0** image (upload/source or image hash and boot/profile evidence).
3. Physical USB link connects that Jetson to that ESP32—not a PC-only or mock transport.
4. PING succeeds with expected ACK command/payload and matching request ID/valid CRC.
5. GET_STATUS succeeds with expected SYSTEM_STATUS command/payload and matching ID/valid CRC.
6. Unplug is detected (node disappearance and failed/timeout probe or API OFFLINE), with timing recorded.
7. Replug is rediscovered, link recovers and PING/GET_STATUS succeed again, with timing recorded.

Servo/pump/sensors must stay disconnected. Sensors and actuators are **not required for M3**. Webcam validation is recommended stage D but is separate from this exact minimum; record any camera failure/deferral rather than claiming it passed. A PC CH343G flash/probe or S3 compile surrogate alone cannot advance M2.

## Exact M4 minimum (later approval-gated work)

AfterM3andpin/electricalreview,separatelyverifyHX711,**currentDS1302**time/CH/WP/readback/retention,food/water,OLED/button/buzzer,thenlaterseparatereviewedservo/pumprigs. RTCchangefromplannedDS3231toavailableDS1302ishistoricalselectionchange,notphysicalPASS. Basicintegratedsafe feed/water withmeasuredoutcomes/limits/cooldown/faults/reset/linklossstillneededforM4;initialrigsnoanimal,outputsstaydisabledinthispass.

Each component and both integrated rigs need actual PASS evidence and reviewed firmware/drivers/power/mechanics. **Current software:** configured sensor/UI diagnostic foundations exist (`M4_DIAGNOSTIC_COMMANDS.md`), but are not hardware verified. Actuator outputs remain hard-disabled; active servo/pump test firmware is not implemented. The earlier “no sensor test drivers” description is HISTORICAL / NOT CURRENT. Do not remove the guard or wire actuators merely because this plan exists. No simulator, crop test, native assertion or predicted sensor value can count as M4.

## Evidence index

Use ignored `evidence/` component folders and the blank log templates. Record timestamp/timezone, component, exact markings/revision, USB connector/node, firmware/image SHA256 or commit, command, expected/actual data, PASS/FAIL/NOT TESTED, screenshot/photo/log names and notes. Request/response IDs, CRC validation and connect/disconnect/recovery timing must be in the serial log. Only manually reviewed actual results can change the milestone.
