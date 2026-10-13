# Report-ready pin table — all physical mappings unverified

GPIO `UNASSIGNED (-1)` is literal current configuration, not a pin recommendation. Voltage notes are nominal candidate interface expectations, not measurements. Verify actual module rails/pull-ups/level shifting first.

| Device | Signal | ESP32-S3 GPIO | Voltage | Direction | Verified? |
| --- | --- | --- | --- | --- | --- |
| HX711 | DOUT | UNASSIGNED (-1) | Actual logic rail pending | Input | NO |
| HX711 | SCK | UNASSIGNED (-1) | MCU3.3V logic, compatibility pending | Output | NO |
| DS3231 | SDA/SCL | UNASSIGNED (-1) | Pull-ups must match MCU; pending | Bidirectional/open-drain | NO |
| SSD1306 | SDA/SCL | UNASSIGNED (-1) | Pull-up/supply pending | Bidirectional/open-drain | NO |
| HC-SR04 | TRIG | UNASSIGNED (-1) | Trigger compatibility pending | Output | NO |
| HC-SR04 | ECHO | UNASSIGNED (-1) | Candidate5V; condition before MCU | Input | NO |
| JSN-SR04T | TRIG | UNASSIGNED (-1) | Variant compatibility pending | Output | NO |
| JSN-SR04T | ECHO | UNASSIGNED (-1) | Actual voltage/conditioning pending | Input | NO |
| Button | Intent input | UNASSIGNED (-1) | MCU logic/pull pending | Input | NO |
| Active buzzer/driver | Pattern control | UNASSIGNED (-1) | Driver/current pending | Output | NO |
| Servo | PWM control | UNASSIGNED (-1) | Separate actuator rail; logic pending | Output disabled | NO |
| Pump MOSFET | Gate control | UNASSIGNED (-1) | Driver/default-OFF pending | Output disabled | NO |

USB/CH343G routing, power and ground are board nets requiring physical identification; they are not guessed application GPIOs. Record the actual reviewed diagram/voltages only after evidence exists.
