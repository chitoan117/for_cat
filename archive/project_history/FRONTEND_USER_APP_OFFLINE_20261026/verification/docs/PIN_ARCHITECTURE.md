# ESP32 GPIO architecture — NOT HARDWARE VERIFIED

Defaultproduction`pins.h`all-1/outputgates0. DeliberateM4sensor-onlycandidateprofileenablesonlytest-targets,notphysicalGPIOPASS:4..13plusDS1302CLK16/DAT17/CE18. NormalHW_SAFEdoesnotinitializeperipherals;ASCIIselecteddiagnosticinitializesonlyitstarget. Servo/pumpremain-1;NoN16R8/PSRAMassumption. `M4_SENSOR_PIN_PROFILE.md` / `DS1302_BRINGUP.md`.

| Interface | Required GPIO role | Verification before pin assignment |
| --- | --- | --- |
| HX711 DOUT / SCK | input / output | safe 3.3 V logic, timing, avoid boot-strapping pins |
| HC-SR04 food TRIG / ECHO | output / input | ECHO may be 5 V; level shift/divide |
| JSN-SR04T water TRIG / ECHO | output / input | ECHO may be 5 V; level shift/divide |
| Servo PWM | timed output | separate servo rail, safe startup and stop |
| Pump MOSFET | digital output | 3.3 V gate drive, safe boot OFF, flyback protection |
| OLEDI2C SDA/SCL |GPIO8/9open-drain |3.3Vpull-ups/supplyandempiricaladdress; noRTC0x68expectation |
| DS1302 CLK/DAT/CE |GPIO16output/17bidirectional/18output |3.3V/modulelabels/CH/WP;hostDATinputbeforereadfallingedge,powerOFFrewire |
| Buzzer | output | drive transistor if needed; current limits |
| Manual Feed button | input | safe pull-up/down, debounce and boot behavior |

GPIO input-only/output-capable, strapping/boot conflicts and shared peripheral pins must be confirmed against the exact ESP32 module/carrier. Use appropriate common ground, separate actuator supply and properly sized wiring. No `ACTUATOR_OUTPUTS_ENABLED=1` build is permitted yet.
