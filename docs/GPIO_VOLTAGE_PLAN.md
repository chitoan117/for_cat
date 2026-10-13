# GPIO voltage plan — all module variants pending

**ESP32-S3 GPIO logic is 3.3 V; do not assume 5 V tolerance.** Any 5 V output toward ESP32 requires a suitable level shifter/divider verified before connection. Power labels are not logic-voltage evidence. Common ground is needed for referenced signals where the reviewed electrical design requires it; never confuse that with powering actuators from logic pins.

| Interface | Check before connection | Required plan |
| --- | --- | --- |
| HX711 digital logic | exact breakout VDD/VSUP/regulator and DOUT voltage; SCK VIH | use compatible digital rail or verified level translation; load-cell excitation is not automatically digital VDD |
| DS3231 breakout | SDA/SCL pull-up rail, battery type and any charging circuit | I2C pull-ups at 3.3 V toward ESP32; shift if module forces 5 V; never fit an unsuitable cell to a charging board |
| SSD1306 module | actual controller/regulator, I2C address/pull-ups | 3.3 V bus; don't infer logic tolerance from module VCC range |
| HC-SR04 ECHO | module variant, powered ECHO peak/high level | suitable divider/buffer/level shifter to ≤3.3 V; verify waveform and ESP32 limits |
| JSN-SR04T ECHO | board revision/interface mode and ECHO high level | same protection, no direct 5 V ECHO connection; verify TRIG VIH too |
| Servo signal | actual MG996R signal thresholds and independent rail | verify 3.3 V PWM acceptance or use correct signal translation; common reference ground, no servo current through GPIO/logic rail |
| MOSFET gate | RDS(on)/current/thermal rating at **3.3 V VGS**, not just VGS(th) | compatible gate drive/pulldown/series protection; rated flyback clamp for pump; no direct pump load on GPIO |

A resistor divider is a signal-level tool, not a power supply or universal I2C solution. Choose/measure values from module characteristics and GPIO maximums; this pack does not prescribe untested resistor values, MOSFETs or supply ratings. Keep all connectors/pins provisional until the identity/electrical worksheet passes.
