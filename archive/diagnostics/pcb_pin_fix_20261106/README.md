# ESP32 PCB pin/role correction — 2026-11-06

Owner scope: firmware and OLED only. No web/backend edits. Water percentages and pump commissioning deferred.

The supplied Proteus ZIP was reread. Its ROOT.LYT bytes exactly match the previously inspected PCB pad/net records; see pcb_evidence.json. Actual physical wire continuity is not established by a design-file comparison.

| PCB | Role | TRIG GPIO | ECHO GPIO |
|---|---|---|---|
| E1 | Cat approach, three fresh readings within 2–30 cm | 12 | 13 |
| E2 | Food reservoir distance | 16 | 17 |
| D1 | Drinking bowl distance | 14 | 15 |
| D2 | Water reservoir distance | 18 | 19 |

D2 ECHO is PCB J3_20=GPIO19, replacing the old GPIO10. The attached USB interface is the USB-UART bridge (1a86:55d3), not native ESP32-S3 USB, which shares GPIO19.

Firmware is based on the actual previously flashed servo-tuned baseline. Servo GPIO6 keeps 1400us/1100ms open, 1600us/1000ms close and 1500us neutral, duplicate-stroke guard and STOP lock. No fine-adjust motion. HX711 median/display/driver/adapter blocks are byte-identical. The legacy early-close trial lead is disabled; the operating feed branch commands closing at the first measured additional mass >=35g. This threshold does not establish an exact physical final dose: food can continue falling while the timed servo closes. No physical dispensing accuracy has been established in this change.

OLED shows six simultaneous rows: weight, feed state, E1 MEO, E2 THUC AN, D1 CHEN, D2 BINH. Distances are cm; invalid readings show --. Labels use ASCII for the installed OLED font.

Legacy UART distance keys are retained for the existing bridge. New explicit pcb_e1_cat_cm, pcb_e2_food_cm, pcb_d1_bowl_cm, pcb_d2_tank_cm fields identify actual roles. Old water calibration is not applied to new roles; percentage returns unknown until future calibration. No new pump feature is deployed. The old local source with pending pump features is backed up as local_pending_before.ino.

Native tests extract actual production branches and verify: 34.99g waits /35g closes; 30cm requires three distinct readings /30.01cm rejected; servo timing boundaries, repeated cycles, duplicate rejection, STOP lock, retry after full close. See native_test_result.txt and integrity_result.json.

Deployment scripts require a flash backup matching the previous app SHA256 8ceb43f5f4939d75b50e25bef8bd226c91c5eaffb4106959f62aaf90a346113a, partition/OTA validation, app-only write/verify and unchanged NVS. No agent feed/open/close/pump test commands are used. Successful deployment must be evidenced by flash_result.json and resume_status.json; this document alone is not proof of a completed flash.

## Final hardware verification

Initial live test exposed a further inherited GPIO policy rejecting19; that prevented D2 initialization and disabled the sensor group. Final firmware explicitly permits D2 input19 while refusing output19, GPIO20, servo6 and pump7 in the sensor adapter. Native tests exercise the actual pin-policy methods as well as mass/distance/servo branches.

Final compile PASS:392801 program bytes,33672 global bytes. Final app SHA25670e5d5aacf62810e2ae721f2b079854427f12c16103d3ab704b011980a6293d8; write/verify PASS. NVS unchanged from the original calibration backup. Final deployment evidence is in final/ and on Jetson /home/toan/for_cat/evidence/pcb_pin_fix_20261106_gpio19.

Actual UART confirmed correct PCB profile, close_trigger_g35, OLED initialized, sensor=1 and four fresh non-timeout channels. Sample distances: E1≈21cm,E2≈316cm,D1≈21cm,D2≈29cm. E2 requires owner inspection of its physical orientation/target before treating this as a food-level reading. No physical feed/pump test was performed. Existing AI request gating remains; E1 proximity alone does not replace AI classification. Existing backend/UI metadata was intentionally unchanged per owner instruction and still contains old GPIO/type labels; the firmware and OLED are the authority for this pin correction.

Original source D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino was synchronized to the verified final candidate. API/bridge/AI are active, sensor reading enabled, feed state READY, no agent actuator command sent. Physical final-dose accuracy remains unverified.
