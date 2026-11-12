# Remove servo fine adjustment

Owner requested removing fine adjustment only. Removed `servo_fine_open`, `servo_fine_close`, their170ms constant, and fine-adjust help/banner text. Full open1400us/1100ms, full close1600us/900ms, neutral1500us and immediate0 stop remain unchanged. Loadcell, feeding logic, ultrasonic sensors, pump, calibration, pin mappings and Jetson software unchanged by this delta. See `change.diff`; exact original source saved in `esp32.before.ino`.

No firmware flashing or physical actuation performed in this step.
