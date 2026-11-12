# ESP32 GPIO architecture — NOT HARDWARE VERIFIED

**2026-10-21 current authority:** `ESP32_S3_SENSOR_STATION.md`,
`config/hardware_current.json`, `esp32/include/current_hardware.h`.
Known selected wiring4..18 is declared there. Runtime actuator pins stay inert;
inventory #2 pairs remainTBD. Removed button12/buzzer13 and ultrasonic6/7/10/11
must not be restored from old instructions. DS1302 is3wire16/17/18, notDS3231I2C.
The placeholder architecture below is historical, not an instruction to replace
current mappings. GPIO candidates1/2 and21/47 are report-only pending owner/header
approval; GPIO48 is excluded because the audited generic variant defines RGB_LED48.

## Historical placeholder architecture

`esp32/include/board_config.h` selects build-safe SIM or GENERIC_ESP32DEV profiles; `pins.h` holds only `UNASSIGNED=-1`. No pin is configured in firmware. Do not attach sensors or actuators based on a placeholder number.

| Interface | Required GPIO role | Verification before pin assignment |
| --- | --- | --- |
| HX711 DOUT / SCK | input / output | safe 3.3 V logic, timing, avoid boot-strapping pins |
| HC-SR04 food TRIG / ECHO | output / input | ECHO may be 5 V; level shift/divide |
| JSN-SR04T water TRIG / ECHO | output / input | ECHO may be 5 V; level shift/divide |
| Servo PWM | timed output | separate servo rail, safe startup and stop |
| Pump MOSFET | digital output | 3.3 V gate drive, safe boot OFF, flyback protection |
| I2C SDA / SCL | bidirectional open-drain | DS3231/SSD1306 voltage, pull-ups and addresses |
| Buzzer | output | drive transistor if needed; current limits |
| Manual Feed button | input | safe pull-up/down, debounce and boot behavior |

GPIO input-only/output-capable, strapping/boot conflicts and shared peripheral pins must be confirmed against the exact ESP32 module/carrier. Use appropriate common ground, separate actuator supply and properly sized wiring. No `ACTUATOR_OUTPUTS_ENABLED=1` build is permitted yet.
