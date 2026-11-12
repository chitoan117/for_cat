# GPIO finalization worksheet — NOT GPIO VERIFIED

Fill candidate columns **only after** physical identity/USB routing/memory reservations are reviewed. No candidate or verified GPIO is assigned in this pack; source `pins.h` remains unassigned. Row names do not imply a verified header mapping.

| SIGNAL | DIRECTION | ELECTRICAL LEVEL | SPECIAL REQUIREMENT | CANDIDATE GPIO | VERIFIED GPIO | SOURCE OF PIN INFORMATION |
| --- | --- | --- | --- | --- | --- | --- |
| HX711_DOUT | input | ≤3.3 V at ESP32 | ready/timeout, module digital supply verified | | | |
| HX711_SCK | output | 3.3 V, module compatibility checked | bounded clocks/power-down behavior | | | |
| FOOD_TRIG | output | 3.3 V compatibility pending | bounded pulse | | | |
| FOOD_ECHO | input | ≤3.3 V after protection | echo edge timing/timeout, possibly 5 V output | | | |
| WATER_TRIG | output | 3.3 V compatibility pending | bounded pulse | | | |
| WATER_ECHO | input | ≤3.3 V after protection | echo timing, waterproof module version/blind zone | | | |
| SERVO_PWM | PWM output | signal compatibility pending | external power, safe boot/closure/jam | | | |
| PUMP_GATE | output | 3.3 V drive compatibility | rated MOSFET, pulldown/off, no pump GPIO power | | | |
| I2C_SDA | bidirectional open-drain | 3.3 V pull-up | RTC/OLED addresses, no hidden 5 V pull-up | | | |
| I2C_SCL | bidirectional open-drain | 3.3 V pull-up | bus timeout/capability | | | |
| BUZZER | output/PWM if passive | driver compatibility pending | current limiting, non-blocking alarm | | | |
| MANUAL_BUTTON | input | 3.3 V with defined pull | debounce; not accidental boot strap | | | |

For every proposal record exact module/carrier schematic page, header pin, GPIO number, input/output/PWM/I2C capability, strapping/reset behavior, USB/JTAG routing and flash/OPI PSRAM exclusions. Cross-check actual board against Espressif documents; another seller's pinout is not evidence. Measure logic levels with peripherals powered separately before connecting outputs to ESP32. Apply `GPIO_VOLTAGE_PLAN.md`; actuator tests require later approved output firmware and M4 precautions, not just a filled table.
