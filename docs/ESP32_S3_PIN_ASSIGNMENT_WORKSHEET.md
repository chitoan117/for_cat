# ESP32-S3 pin worksheet — NOT GPIO VERIFIED

Candidate only: seller 44-pin ESP32-S3 N16R8 board, 16 MB flash, 8 MB PSRAM, Type-C, external antenna. No purchased board has been identified. `esp32-s3-devkitc-1` is **COMPILE SURROGATE ONLY**, NOT EXACT SELLER BOARD VERIFIED / NOT HARDWARE VERIFIED. `board_config.h` selects classic or S3 without application pin constants; `pins.h` leaves all signals `PIN_NOT_ASSIGNED=-1`, and safe builds fail if those are assigned prematurely.

For **every row**, check the exact module/carrier, input-only capability, strapping/reset state, USB/JTAG use, flash/PSRAM reservations and 3.3 V logic—not just silkscreen numbers. This worksheet deliberately has no final pin numbers.

| Signal | Required direction/peripheral | Interrupt/PWM requirement | Electrical / boot concerns | Proposed GPIO / evidence |
| --- | --- | --- | --- | --- |
| HX711_DOUT | digital input | optional ready-edge interrupt, or bounded polling | output voltage, pull-up, safe boot | NOT ASSIGNED |
| HX711_SCK | digital output | bounded clock timing; no PWM required | avoid unwanted power-down pulses/strap | NOT ASSIGNED |
| FOOD_TRIG | digital output | bounded trigger pulse | 3.3 V trigger compatibility | NOT ASSIGNED |
| FOOD_ECHO | digital input | edge timing interrupt desirable, bounded timeout | HC-SR04 may output 5 V; divider/level shifter required | NOT ASSIGNED |
| WATER_TRIG | digital output | bounded trigger pulse | waterproof module variant must be identified | NOT ASSIGNED |
| WATER_ECHO | digital input | edge timing interrupt desirable | JSN-SR04T ECHO may be 5 V | NOT ASSIGNED |
| SERVO_PWM | PWM-capable output | hardware timed servo PWM | independent servo supply, boot/jam/closure safety | NOT ASSIGNED / HARD-DISABLED |
| PUMP_CONTROL (`PUMP_MOSFET`) | digital output | PWM not required for on/off | 3.3 V MOSFET gate compatibility, pulldown/off at reset | NOT ASSIGNED / HARD-DISABLED |
| I2C_SDA | bidirectional open-drain | I2C routing | correct 3.3 V pull-ups and addresses | NOT ASSIGNED |
| I2C_SCL | bidirectional open-drain | I2C clock routing | check clock stretch/bus voltage | NOT ASSIGNED |
| BUZZER | digital output (PWM if passive buzzer) | depends on buzzer type | current/driver, reset sound state | NOT ASSIGNED |
| MANUAL_FEED_BUTTON | digital input | debounce polling; optional interrupt | pull-up/down and boot strap interaction | NOT ASSIGNED |

Espressif's S3 GPIO documentation lists strapping GPIO0/3/45/46; USB-JTAG uses 19/20; SPI flash/PSRAM commonly use 26–32 and Octal memory may also reserve 33–37. These are **silicon warnings, not a seller board pinout**. Check the module datasheet (including any input-only limitations), schematic and SDK capability masks before proposing any GPIO. Classic ESP32 pin restrictions must not be copied onto S3 blindly. Reference: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/gpio.html

## Pin finalization gate (all unchecked tonight)
- [ ] Exact seller/carrier photographed and module marking confirmed.
- [ ] N16R8 marking and actual flash/PSRAM capacities verified on device.
- [ ] Official module pinout cross-checked against seller/carrier schematic and header continuity.
- [ ] Flash/PSRAM reserved pins excluded; USB/JTAG interface and pins preserved.
- [ ] Strapping/reset behavior checked; input-only/output/PWM/I2C capabilities verified.
- [ ] GPIO/level/shifter voltages measured; ultrasonic ECHO protection planned before wiring.
- [ ] Safe USB PING/GET_STATUS and reconnect gate passed, with no peripherals attached.
- [ ] A separately reviewed physical pin profile and tests created; none labelled VERIFIED merely from compilation.

Keep servo/pump disconnected. No GPIO assignment becomes VERIFIED during RC2.
