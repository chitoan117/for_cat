# ESP32 GPIO architecture — NOT HARDWARE VERIFIED

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
