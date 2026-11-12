# PHYSICAL_VALIDATED_ARDUINO_HX711_REFERENCE

- Owner-provided, physically tested Arduino UNO + current HX711/load-cell assembly.
- Original code: `C:\Users\chito\OneDrive\Desktop\CODE_TEST_LOADCELL_CHUAN\CODE_TEST_LOADCELL_CHUAN.ino` (307 lines, read in full).
- Original serial evidence: `C:\Users\chito\OneDrive\Desktop\CODE_TEST_LOADCELL_CHUAN\data_test.txt` (791 lines, read in full). A byte-identical copy is archived here as `data_test.txt`; SHA256 `4b65836701e5630f8f540d45d759803514e1fd3a39f3a321dfe52286cb4c731e`.
- Full code archived alongside this note before modifying ESP32 source. Original SHA256 `8d4871be23c12bc4e9441ee3f727f0d0b229d430411b61a2ada7619c7c71f139`; archive SHA256 `4b12d63645c9aa3b37b0f79584afb0034c8676c0bd1fa09733a18e3c9b582135`. Only difference: the archive has a final newline; original has none. `verify.py` checks normalized-text equality and records both hashes.
- Historical Arduino calibration: offset -668483 counts; scale -1064.4473 counts/gram. Diagnostic comparison only, not permanent ESP32/mounting authority.
- Owner hardware authority: HX711 board supply **5V**, ESP32-S3 DOUT **GPIO4**, SCK **GPIO5**. No pin-map change.
- The supplied log contains steady plateaus around 4.92–4.98g, 9.91–9.98g, 19.89–20.00g and 37.92–38.06g, as well as large unlabelled transients and zero shifts. Preserve the entire original log; do not label every line a stable-weight PASS or invent placement/timing labels.
- The golden algorithm is median of three consecutive raw conversions, A/128 signed24, ready timeout, explicit multi-sample tare, signed mass formula, 0.20g deadband, >=1g immediate update and alpha 0.40 otherwise.
- The additional reference clamp `-0.5g < mass < 0g` is display-only in the port. Signed pre-deadband measurements remain visible for drift checks.
- ESP32 physical status: **NOT_TESTED**. Software tests and builds cannot establish ESP32 accuracy, electrical timing, mounting stability or zero recovery.
