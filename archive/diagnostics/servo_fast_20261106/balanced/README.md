# Accepted servo travel profile — 2026-11-06

Owner accepted after3 physical cycles: OPEN RIGHT1350us/900ms; CLOSE LEFT1600us/1450ms; neutral1500us. The opening pulse is faster than the former1400us; closing duration is extended to bias relative travel toward closing. No separate fine-adjust movement is introduced. Three accepted cycles are not an absolute-position measurement or proof across every food load/supply condition.

The owner had reported900ms opening correct but1050ms closing insufficient with accumulated drift. After realigning CLOSED,1450ms closing was tried via RAM, and the owner explicitly answered “Đóng đúng mốc sau3 lượt”. Full acceptance is recorded in owner_acceptance.json. The mechanical stop does not cut servo power; firmware must still end the closing command after1450ms and return to neutral.

Extracted production branch tests PASS: timing boundaries at900/1450, alternating cycles, duplicate stroke rejection, STOP inspection lock, full-close retry, GPIO19 input policy, E1≤30cm3 readings, mass34.99g wait/35g closing command. HX711/sensor/feed logic and Jetson DOG confirmation filter are unchanged. NVS scale calibration is preserved during app-only programming.

Final binary SHA256a23efe87f2d502f0f4aad27a0aab5cf2b140b04a06ba2f5e8f4bdf878da2aa47. Source of truth after successful synchronization: D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino. Jetson evidence: /home/toan/for_cat/evidence/servo_balanced_20261106. Prior750/1050 app and full backup retained for rollback. Check flash_result.json/resume_verified.json for actual deployment verification rather than relying on this document alone.
