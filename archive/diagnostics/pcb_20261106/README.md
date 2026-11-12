# FOR_CAT PCB review — 2026-11-06

## Follow-up: original UNO references restored and checked

Found original scale reference at `D:/CODE_TEST_LOADCELL_CHUAN/CODE_TEST_LOADCELL_CHUAN.ino`, with offset-668483 and scale-1064.4473, median3, zero deadband0.20g, fast change1g, stable alpha0.40. The ESP32 HX driver/conversion/filter already matches that algorithm and remains unchanged. Extracted actual ESP32 and original UNO code comparisons PASS for median permutations and1600 signed conversion/display samples. Servo regression PASS for1400us/1100ms open,1600us/900ms close,1500us neutral,170ms fine. Commands1/2 retain CAT/DOG meanings for Jetson;3/4 are full manual strokes.

Added `T` alias for UNO tare compatibility; `servo_uno` restores calibrated motion durations while idle without movement; explicit `cal_uno` imports the historical UNO offset/scale into ESP32 NVS only on user command while idle with fresh HX raw, preserving other geometry. No automatic overwrite of existing NVS at boot. An imported historical scale still needs real empty/38g checks. No such command was sent to hardware.

Final compile PASS:407737 program bytes,33736 global bytes. Updated actual source `D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino` from the compiled candidate after checking the target still matched the saved backup. Earlier statements below saying the original sketch was not replaced are superseded by this follow-up. Firmware has NOT been flashed in this follow-up; live Jetson backend unchanged, candidate backend only syntax checked. Pump remains disabled until explicit calibration/target/enable.

Input: C:/Users/chito/Downloads/pet_feeder.pdsprj. ZIP contains ROOT.LYT (91930 bytes), ROOT.DSN, ROOT.CDB and project metadata. Original project was not edited. PCB was opened/viewed in Proteus. Connectivity was also read from embedded pad net-name records in ROOT.LYT; this is not a fabricated schematic export. Proteus displayed no CRC/DRC errors at the viewed state; this does not establish electrical correctness or physical wiring.

## PCB connectivity versus old sketch

| PCB | Purpose supplied by owner | TRIG net / GPIO | ECHO net / GPIO |
|---|---|---|---|
| E1 | Cat approach | J1_18 / 12 | #00025 → R7 10k → J1_19 / 13; R8 20k to GND |
| E2 | Food reservoir | J1_9 / 16 | #00039 → R5 10k → J1_10 / 17; R6 20k to GND |
| D1 | Drinking bowl | J1_20 / 14 | #00021 → R11 10k → J1_8 / 15; R12 20k to GND |
| D2 | Water reservoir | J1_11 / 18 | #00030 → R9 10k → J3_20 / 19; R10 20k to GND |

GPIO19 replaces old GPIO10 for D2. Header J3_20 is GPIO19 per Espressif ESP32-S3-DevKitC-1 pin table: https://docs.espressif.com/projects/esp-idf/en/v4.4.8/esp32s3/hw-reference/esp32s3/user-guide-devkitc-1.html . Use USB-to-UART for this mapping; GPIO19 is also native USB D-.

Servo net J1_6=GPIO6; pump optocoupler LED path GPIO7/J1_7→R3→PC817; PC817 pulls PMOS IRF4905 gate low, so GPIO HIGH requests pump ON. Button J3_18=GPIO21; buzzer J3_5=GPIO2. HX711 GPIO4/5 and OLED8/9 retained. Physical measurements and wiring polarity were not tested. HX711 connector +5V/digital output voltage requires actual module-level verification, as pin labels alone do not establish module logic voltage.

## Prepared firmware (not flashed)

`esp32/esp32.ino` is a candidate based on the actual current sketch; original backed up as `esp32.before.ino`.

- E1 5..30cm, 3 consecutive fresh raw readings. CAT recognition/request and calibrated fresh HX711 conditions remain.
- Four HC-SR04 2..400cm; E2=16/17, D1=14/15, D2=18/19.
- HX711 conversion/filter/NVS routines unchanged; servo 1400us/1100ms open,1600us/900ms close,1500us neutral,170ms fine unchanged. Existing30..40g measured close principle retained.
- Independent geometry NVS `fc_pcb_v1`, never importing old geometry into new sensor roles.
- `level_cal E2|D1|D2 full_cm empty_cm` configures measured distances, not arbitrary container height. Values must be2..400cm, empty-full>=0.5cm.
- `pump_target PERCENT` requires >50..100; no target assumed until owner clarifies. `pump_auto on` requires D1/D2 calibration and fresh readings. Off at boot pending physical commissioning. `pump_auto off`, `pump_reset`, numeric0,stop,STOP,sensors_off disable pump.
- Starts below50% after3 distinct D1 readings; stops at configured target, invalid/stale D1/D2, empty D2.30s maximum run latches a fault requiring reset.30s bound is provisional and needs measured flow/overflow commissioning.
- Percentages are relative distance-based level, not a verified volume percentage for a tapered container.
- D2 empty inhibits pump; separate telemetry reports water reservoir percentage. No unknown reading is treated as empty/zero.

Native water logic and existing servo/mass regression tests PASS. These use actual extracted code with fake hardware. They do not prove real pump flow, measurement accuracy or electrical safety. See test result files. Arduino ESP32-S3 core3.3.12 compile PASS:407001 program bytes,33736 globals.

## Prepared backend (not deployed)

`fc_live_bridge.py`, `ultrasonic_state.py`, `system_state.py`, `hardware_current.json`. Channel IDs preserved for installed Flutter compatibility (two IDs still contain legacy JSN text), while actual type/role/pins become HC-SR04 and correct PCB role. Syntax checked. Remove old invented5/35cm percentage mapping; food comes from E2, bowl from D1, tank from D2 with firmware-calibrated geometry. These backend edits still require runtime tests before deployment.

## Outstanding

Owner must supply full/empty distances for E2,D1,D2 and clarify D1 refill stopping level (the request could mean100% or50%). Need verify physical sensor orientation, especially minimum2cm clearance above water. Pump stays disabled until commissioning.

At read-only Jetson audit, API/bridge services were active, USB bridge1a86:55d3 serial5C85066678 appeared at ttyACM0, but API ESP32 telemetry was disconnected/stale. No servo/feed/pump command was sent in this review. Earlier device-specific ModemManager rule still absent from active udev properties (ID_MM_CANDIDATE=1); administrator installation remains pending. No source on live Jetson or original Arduino sketch was replaced, no firmware flashed, and no hardware pass claimed.
