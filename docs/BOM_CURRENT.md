# Candidate BOM worksheet — no prices supplied

SELECTED means architectural role selected, not purchased/tested. CANDIDATE means a proposed component; PENDING VERIFICATION means specifications/wiring/ratings remain open. Quantities depend on the final physical rig.

| Item | Role | Status | Verification needed |
| --- | --- | --- | --- |
| Jetson Nano | Local vision/API/storage | SELECTED | Actual revision/OS/JetPack/power/runtime |
| Normal USB webcam | Video input | SELECTED | Exact model, Linux backend, mount/lighting |
| ESP32-S3 N16R8 seller board | Sensor/safety MCU | CANDIDATE | Exact board/module, flash/PSRAM, ports/header |
| Load cell 5kg | Food mass | CANDIDATE | Rated range, wiring, bowl mount, calibration |
| HX711 | Load-cell ADC | CANDIDATE | Module supply/logic/gain/readiness |
| HC-SR04 | Candidate food distance | CANDIDATE | Actual range/ECHO voltage/mount |
| JSN-SR04T | Candidate water distance | CANDIDATE | Variant, minimum range/wet-surface behavior |
| DS3231 | RTC | CANDIDATE | Module/battery/pull-up voltage/retention |
| SSD1306 | Minimal status panel | CANDIDATE | Address/height/interface/supply |
| Buzzer | Status patterns | CANDIDATE | Active vs passive, current/driver |
| Manual button | Feed intent | CANDIDATE | Polarity/pull/wiring/debounce |
| MG996R | Candidate food gate servo | CANDIDATE | Supply/current/closure/jam mechanics |
| 5V pump | Water rig | CANDIDATE | Actual rated current/flow/dry-run/stop |
| MOSFET | Pump switching | PENDING VERIFICATION | Logic level, ratings, wiring/default-OFF |
| Flyback diode | Inductive protection | PENDING VERIFICATION | Pump current/voltage/polarity |
| Power supplies | Jetson/MCU/actuator rails | PENDING VERIFICATION | Ratings, common ground, transient behavior |
| Level shifting | 5V signals to MCU | PENDING VERIFICATION | Actual ECHO/pull-up voltages |
| Wiring/connectors/fusing | Reliable protected interconnect | PENDING VERIFICATION | Gauge, polarity, disconnects |
| Bowl/gate/mount/tubing/enclosure | Mechanical/food-water containment | PENDING VERIFICATION | Hygiene, stability, leaks, pinch/jam |

No price, final GPIO or electrical rating is invented. Refer to `PIN_TABLE_TEMPLATE.md`; actuator interfaces remain disabled.
