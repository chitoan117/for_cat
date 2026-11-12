# Hardware — current declared contract 2026-10-21

USB webcam -> Jetson Nano2GB C++14/OpenCV/TensorRT FP16 YOLOv8n -> CAT/DOG/NONE.
USB serial -> ESP32-S3 (16MB,noPSRAM,2cores,240MHz), final actuator safety authority.
Current GPIO/staged validation authority: `ESP32_S3_SENSOR_STATION.md` and
`config/hardware_current.json`; firmware declarations in `include/current_hardware.h`.

Inventory:HX711/loadcellx1,PIRHC-SR501x1,HC-SR04x2(approach/hopper),JSN-SR04TV3x2
(operationalwater/reservoir),servox1,pump5V/F5305Sx1,SSD1306OLED0x3C,DS1302RTC.
HC-SR04#2 and JSN#2 TRIG/ECHO stayTBD. DS3231, button12/buzzer13, oldfood6/7 and
water10/11 assignments are STALE for this assembly. Normal inert `pins.h` remains
unassigned deliberately; wiring constants do not attach outputs or grant permission.

External5V supply uses separate Jetson/ESP32VIN/servo/pump/sensor branches, not
dynamic pump/servo load from Jetson header. HX711/OLED/DS1302 use verified appropriate
3V3 rails. Common logic reference/power polarity/backfeed and supply-current margin
must be checked on actualmodules. ECHO5V requires divider10k/20k to~3.3V.

Desired feed is **added** delta≈40g with pulse-close-settle scale feedback, not a
fixed angle or total bowl weight. Existing portable safety/disabled drivers are
not complete physical PWM control. Water refill uses operational water evidence,
not DRINKING AI. Current outputs stay0 and no actuator command was added.
Actual new assembly wiring/voltage/retention/accuracy/flow/closure are NOT TESTED.
Owner reports prior UART/OLED/RTC/HXbring-up; do not promote that to integratedPASS.
