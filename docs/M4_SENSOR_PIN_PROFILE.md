# Current S3 sensor-only candidate mapping

Chip/flash physically reported verified: S3 revv0.2,40MHz,16MB; **PSRAM NOT DETECTED**. Use no-PSRAM bridge profiles, never seller N16R8 flags. `pins.h` remains entirely-1; `board_profile::gpio_verified=false` and ACTUATOR_OUTPUTS_ENABLED=0 stay enforced. Explicit `M4_SENSOR_BRINGUP=1` diagnostic profiles use separate `m4/candidate_sensor_pins.h`, not production actuator mapping.

| Test signal | Candidate GPIO | Connection/review |
| --- | ---: | --- |
| I2C SDA/SCL |8/9 |3.3V-compatible pull-ups, shared ground, actual module supply/charging review |
| RTC DS1302 CLK/DAT/CE |16/17/18 |3.3V mainlogic/supply; DAT17 bidirectional; CE/RSTactiveHIGH, separate fromI2C |
| HX711 DOUT/SCK |4/5 | Identify module logic/excitation/cell leads, mount/unload before calibration |
| Food TRIG/ECHO |6/7 | GPIO7 MUST NOT receive5V; divider/level shift and actual range review |
| Water TRIG/ECHO |10/11 | GPIO11 MUST NOT receive5V; divider/level shift; actual JSN variant/blind zone |
| Manual Feed button |12 | INPUT_PULLUP active LOW: button to GND, no servo action |
| Buzzer |13 | Candidate only; unknown active/passive/module/current/polarity, driver disabled until explicit review/command |
| Servo / pump |**UNASSIGNED (-1)** | Future candidates14/15 DOCUMENTED ONLY, no output/wiring/driver enable |

Reserved:0 boot,43/44 current UART bridge,19/20 native USB,38 RGB; conservative special/strap/memory/JTAG exclusions remain. No static pin assertion or candidate declaration verifies physical board routing/voltage. Stage one module at a time with power off for wiring; servo/pump electrically disconnected.

Candidate profile is intentional config attestation (`M4_PINS_REVIEWED=1`), **not GPIO/hardware PASS**. Compile guards reject no-PSRAM profile with BOARD_HAS_PSRAM (even=0), explicit PSRAM enable, native-USB/CDC conflict, SIM mixing, normal-mode candidate activation, pin-override conflicts or actuator pins/flags. Shared SDK CONFIG_SPIRAM capability is not board enable; the initial overstrict guard was corrected after actual build failure, retaining all application/output protections.

**RTC hardware changed from planned DS3231 to available DS1302 during M4 physical bring-up.** OLED alone remains8/9I2C; RTC16/17/18 are explicitcandidateprofileonly, defaultpins-1. Compile/static checks require uniqueGPIOs, no sensor overlap or0/14/15/19/20/38/43/44 conflict. With powerOFF:3V3→DS1302VCC,GNDcommon,16→CLK,17→DAT/IO,18→RST/CE; actual module label order must be verified. No RTCphysicalPASS; `DS1302_BRINGUP.md` documents CH/WP/readback and notI2C.

Ultrasonic1..400cm are broad **software sanity bounds**, not calibrated hardware range/blind-zone specs. Unknown/unconfigured geometry yields no percent. Before any echo acquisition measure/review divider/shifter result≤3.3V and actual module limits; then terminal `echo-3v3 CONFIRM` enables only the selected sensor. Startup does not toggle trigger before that acknowledgment. Do not acknowledge for a bare5V ECHO wire; stop on blind-zone/impossible/unstable readings. Buzzer GPIO remains untouched until a reviewed active-high safe driver and `buzzer-driver ACTIVE_HIGH CONFIRM`, then bounded `buzz` pattern. Passive buzzer tone is not implemented.
