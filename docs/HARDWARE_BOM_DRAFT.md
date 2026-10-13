# Hardware BOM draft — no parts or pinout validated

Historical draft navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL / NOT CURRENT selection worksheet:** the old generic ESP32 / named webcam entries are draft candidates, not a second architecture. Current BOM is `BOM_CURRENT.md`; MCU is ESP32-S3 N16R8 candidate, camera is a normal USB webcam with exact model pending verification.

| Group | Planned part | Confirmation |
| --- | --- | --- |
| Compute | Jetson Nano with appropriate carrier, storage and cooling | revision and supply PENDING HARDWARE CONFIRMATION |
| Camera | Logitech USB webcam and suitable USB cable | model PENDING HARDWARE CONFIRMATION |
| MCU | ESP32 development board, USB serial cable | exact model PENDING HARDWARE CONFIRMATION |
| Food mass | 5 kg load cell + HX711 amplifier | calibration/mount PENDING |
| Food level | HC-SR04 ultrasonic module | voltage/echo level PENDING |
| Water level | JSN-SR04T ultrasonic module | voltage/echo level PENDING |
| Feed actuator | MG996R servo and mechanical gate | servo output DISABLED |
| Water actuator | 5 V mini pump, suitable MOSFET stage and flyback diode | pump output DISABLED |
| Time/display | DS3231 RTC with battery, SSD1306 OLED | I2C address and voltage PENDING |
| Local alerts | buzzer and Manual Feed pushbutton | debouncing/pull-up PENDING |
| Power | Jetson supply and separately rated actuator 5 V rail, protection, bulk capacitors | exact supplies PENDING HARDWARE CONFIRMATION |
| Assembly | connectors, appropriately sized wiring, strain relief, enclosure, food-safe bowl/tube/mount | mechanical compatibility PENDING |

Review `POWER_AND_ELECTRICAL_SAFETY.md` and `HARDWARE.md` before ordering or energizing anything.
