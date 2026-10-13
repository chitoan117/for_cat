# M4 driver audit — starting state, then implementation

Starting source inspected: `esp32/src/main.cpp`, `include/{sensor_drivers,hardware_interfaces,safety_logic,safety_persistence,pins,board_config}.h`, PlatformIO profiles and native harness. M3 pack is already complete and is **not recreated** in this task.

| Component | Initial classification | Initial evidence / missing work |
| --- | --- | --- |
| HX711 | INTERFACE ONLY / SIMULATION ONLY | alias/interface and injected grams; no actual ready/clock/raw/tare/calibration driver |
| DS3231 | INTERFACE ONLY | clock validity/epoch contract, no I2C/BCD read/set |
| Food ultrasonic | PLACEHOLDER / SIMULATION ONLY | available flag/interface, no trigger/echo/filter/geometry |
| Water ultrasonic | PLACEHOLDER / SIMULATION ONLY | injected level/policy, no real echo/acquisition/calibration |
| SSD1306 | INTERFACE ONLY / SIMULATION ONLY | status/sim text, no actual panel transport/framebuffer |
| Manual button | IMPLEMENTED (portable debounce only) / INTERFACE ONLY (GPIO) | no configured polarity/pull or real input adapter |
| Buzzer | INTERFACE ONLY / SIMULATION ONLY | no real non-blocking GPIO pattern driver |
| Servo | INTERFACE ONLY / SIMULATION ONLY | inert/sim outputs; no real PWM, deliberately disabled |
| Pump | INTERFACE ONLY / SIMULATION ONLY | inert/sim outputs; no real switching, deliberately disabled |
| Health/snapshot | PLACEHOLDER | old OK/FAULT contract, no complete optional local component snapshot |
| Sensor calibration persistence | NOT IMPLEMENTED | safety counters exist separately, no measured-sensor record |
| Component diagnostics | NOT IMPLEMENTED | normal binary protocol only; no raw sensor test builds |

All physical components **REQUIRE HARDWARE** for actual verification. Implementation continues in `esp32/include/m4/` and explicit diagnostic profiles, not guessed production GPIOs. `M4_PRE_HARDWARE_PREPARATION.md` records the final implementation/tests/compile evidence and remaining gates.

## Implemented end state (software classification)

| Component | Current classification | Code evidence | Physical classification |
| --- | --- | --- | --- |
| HX711 | IMPLEMENTED | `m4/hx711.h`, `calibration.h`, injected real pin adapter | REQUIRES HARDWARE |
| DS3231 | IMPLEMENTED | `m4/rtc.h`, bounded I²C adapter | REQUIRES HARDWARE |
| I²C scanner | IMPLEMENTED | `m4/rtc.h::I2CScanner` | REQUIRES HARDWARE |
| Ultrasonic core | IMPLEMENTED | `m4/ultrasonic.h::Ultrasonic` | REQUIRES HARDWARE |
| Food level | IMPLEMENTED | independent `LevelSensor` and `LevelCalibration` | REQUIRES HARDWARE |
| Water level | IMPLEMENTED | independent `LevelSensor` plus shadow policy bridge | REQUIRES HARDWARE |
| SSD1306 | IMPLEMENTED | `m4/oled.h` setup/framebuffer/chunks | REQUIRES HARDWARE |
| Manual button | IMPLEMENTED | `m4/accessories.h::ManualButton` | REQUIRES HARDWARE |
| Active buzzer | IMPLEMENTED | `m4/accessories.h::Buzzer` and bounded patterns | REQUIRES HARDWARE |
| Servo | INTERFACE ONLY | `m4/actuator_interfaces.h::DisabledServo`; PWM NOT IMPLEMENTED | REQUIRES HARDWARE |
| Pump | INTERFACE ONLY | `m4/actuator_interfaces.h::DisabledPump`; switching NOT IMPLEMENTED | REQUIRES HARDWARE |
| Health/snapshot | IMPLEMENTED | `m4/health.h`, `snapshot.h` | Real input validation REQUIRES HARDWARE |
| Calibration persistence | IMPLEMENTED (codec/adapter preparation) | `m4/calibration_record.h`, `arduino_io.h` | NVS behavior REQUIRES HARDWARE |
| Component diagnostics | IMPLEMENTED | `src/diagnostics.cpp`, six explicit PlatformIO modes | Runtime bench results REQUIRES HARDWARE |

Portable tests drive the actual acquisition classes through fake I/O; these are not hardware validation or simulated production measurements.
