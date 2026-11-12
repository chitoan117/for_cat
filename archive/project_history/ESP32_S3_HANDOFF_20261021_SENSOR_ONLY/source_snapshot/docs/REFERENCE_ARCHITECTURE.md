# Reference architecture — canonical 2026-10-21

```text
USB camera -> Jetson Nano2GB -> OpenCV C++14 / CUDA / TensorRT FP16 / YOLOv8n
                                            CAT / DOG / NONE (working)
                                                     |
                 CAT + HC-SR04 #1 stable near + safety (planned)
                                                     |
AUTO ~40g ADDED / SCHEDULE bounded target / MANUAL bounded target
                        -> ONE FEED ARBITER (planned)
                        -> USB Serial -> ESP32-S3 16MB/noPSRAM
                        -> final safety -> servo pulse/CLOSE/settle/HX711

CAT/track/FOOD_ROI + filtered meaningful negative weight trend
                        -> eating FSM / consumed grams / visits (planned)
JSN-SR04T #1 operational water -> ESP32 water safety -> F5305S/pump (planned)
HC-SR04 #2 hopper + JSN-SR04T #2 water reservoir (GPIO TBD)
                        -> calibrated inventory / LOW alerts (planned)

ONE backend + ONE SQLite + ONE REST API + ONE responsive Web (target)
                        /kiosk local touchscreen | /app phone/admin
                        -> history / meal plan / later preference & prediction
```

AI runs on Jetson, never ESP32/webcam. ESP32 is final actuator authority.
OWNER_CAT/OTHER_CAT is optional future work. No new EATING NN prerequisite now.
DRINKING never controls pump. Internet loss does not stop localhost kiosk; offline
ESP32 schedule fallback is future revisioned/single-owner work, not already deployed.

Classic and N16R8 profiles are regression/legacy surrogates; current declared board
is16MB/noPSRAM/UART0bridge. Current vendor PCB header details remain physically
unverified. `current_hardware.h` declares wiring; normal inert `pins.h` remains
unassigned and all actuator flags0. ASCII schema2 diagnostics are separate from
normal binary UARTv1; telemetry DB/API and control extensions are still TODO.

`CURRENT_PROJECT_STATE.md` distinguishes actual source, owner evidence and planned
arrows. `ESP32_S3_SENSOR_STATION.md` owns pin/physical procedure; `ROADMAP.md` owns
the incremental acceptance order. Existing FastAPI/SQLite source is host-tested,
not a Python vision replacement or a claimed Nano deployment. Historical M2 docs,
dataset-absent/AI-untrained and all-pins-unassigned claims are stale globally.
No diagram arrow is proof of integrated physical PASS or permission to actuate.
